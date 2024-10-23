// index.js

const TelegramBot = require('node-telegram-bot-api');
const Groq = require('groq-sdk');
const axios = require('axios');

// API Keys and Configuration
const groqApiKey = '';
const azureApiKey = '';
const azureEndpoint = '';
const telegramBotToken = '';

// Initialize clients
const groq = new Groq({ apiKey: groqApiKey });
const bot = new TelegramBot(telegramBotToken, { polling: true });

// Store user preferences and conversation history
const userPreferences = new Map();
const conversationHistory = new Map();

// Class to manage conversation context
class ConversationManager {
  constructor(maxMessages = 10) {
    this.maxMessages = maxMessages;
  }

  // Initialize conversation for a user
  initConversation(chatId) {
    if (!conversationHistory.has(chatId)) {
      conversationHistory.set(chatId, []);
    }
  }

  // Add message to conversation history
  addMessage(chatId, role, content) {
    this.initConversation(chatId);
    const history = conversationHistory.get(chatId);
    history.push({ role, content });
    
    // Keep only the last maxMessages
    while (history.length > this.maxMessages) {
      history.shift();
    }
    
    conversationHistory.set(chatId, history);
  }

  // Get conversation history
  getHistory(chatId) {
    this.initConversation(chatId);
    return conversationHistory.get(chatId);
  }

  // Clear conversation history
  clearHistory(chatId) {
    conversationHistory.set(chatId, []);
  }
}

const conversationManager = new ConversationManager(10);

// Function to get Groq API response with context
async function getGroqChatCompletion(chatId, message) {
  try {
    const history = conversationManager.getHistory(chatId);
    const response = await groq.chat.completions.create({
      messages: [
        ...history,
        {
          role: 'user',
          content: message,
        },
      ],
      model: 'llama3-8b-8192',
      temperature: 0.7,
      max_tokens: 1024,
    });
    
    const assistantResponse = response.choices[0]?.message?.content || 'Desculpe, não consegui obter uma resposta.';
    
    // Save both user message and assistant response to history
    conversationManager.addMessage(chatId, 'user', message);
    conversationManager.addMessage(chatId, 'assistant', assistantResponse);
    
    return assistantResponse;
  } catch (error) {
    console.error('Erro ao chamar a API Groq:', error);
    return 'Desculpe, ocorreu um erro ao processar sua solicitação.';
  }
}

// Function to get Azure OpenAI response with context
async function getAzureOpenAICompletion(chatId, message) {
  try {
    const history = conversationManager.getHistory(chatId);
    const response = await axios.post(
      azureEndpoint,
      {
        messages: [
          ...history,
          {
            role: 'user',
            content: message,
          },
        ],
        temperature: 0.7,
        max_tokens: 1024,
      },
      {
        headers: {
          'Content-Type': 'application/json',
          'api-key': azureApiKey,
        },
      }
    );
    
    const assistantResponse = response.data.choices[0]?.message?.content || 'Desculpe, não consegui obter uma resposta.';
    
    // Save both user message and assistant response to history
    conversationManager.addMessage(chatId, 'user', message);
    conversationManager.addMessage(chatId, 'assistant', assistantResponse);
    
    return assistantResponse;
  } catch (error) {
    console.error('Erro ao chamar a API Azure OpenAI:', error);
    return 'Desculpe, ocorreu um erro ao processar sua solicitação.';
  }
}

// Function to show the main menu
function showMainMenu(chatId) {
  const options = {
    reply_markup: {
      inline_keyboard: [
        [
          { text: '🤖 Usar Groq', callback_data: 'use_groq' },
          { text: '🔷 Usar Azure OpenAI', callback_data: 'use_azure' },
        ],
        [
          { text: '❓ Modelo Atual', callback_data: 'check_current' },
          { text: '🗑️ Limpar Histórico', callback_data: 'clear_history' },
        ],
        [{ text: '📜 Ver Histórico', callback_data: 'view_history' }],
      ],
    },
  };
  bot.sendMessage(chatId, 'Escolha uma opção:', options);
}

// Format conversation history for display
function formatHistory(history) {
  return history.map((msg, index) => {
    const roleEmoji = msg.role === 'user' ? '👤' : '🤖';
    return `${roleEmoji} ${msg.role}: ${msg.content}`;
  }).join('\n\n');
}

// Handle callback queries from inline keyboard
bot.on('callback_query', async (query) => {
  const chatId = query.message.chat.id;
  
  switch (query.data) {
    case 'use_groq':
      userPreferences.set(chatId, 'groq');
      await bot.answerCallbackQuery(query.id);
      bot.sendMessage(chatId, 'Agora usando o modelo Groq! Pode enviar sua mensagem.');
      break;
      
    case 'use_azure':
      userPreferences.set(chatId, 'azure');
      await bot.answerCallbackQuery(query.id);
      bot.sendMessage(chatId, 'Agora usando o modelo Azure OpenAI! Pode enviar sua mensagem.');
      break;
      
    case 'check_current':
      const currentModel = userPreferences.get(chatId) || 'não definido';
      await bot.answerCallbackQuery(query.id);
      bot.sendMessage(chatId, `Modelo atual: ${currentModel}`);
      break;
      
    case 'clear_history':
      conversationManager.clearHistory(chatId);
      await bot.answerCallbackQuery(query.id);
      bot.sendMessage(chatId, 'Histórico de conversa limpo!');
      break;
      
    case 'view_history':
      const history = conversationManager.getHistory(chatId);
      await bot.answerCallbackQuery(query.id);
      if (history.length === 0) {
        bot.sendMessage(chatId, 'Ainda não há histórico de conversa.');
      } else {
        bot.sendMessage(chatId, `📜 Histórico das últimas ${history.length} mensagens:\n\n${formatHistory(history)}`);
      }
      break;
  }
});

// Handle received messages
bot.on('message', async (msg) => {
  const chatId = msg.chat.id;
  const userMessage = msg.text;

  if (!userMessage) return; // Ignore non-text messages

  // Handle commands
  switch (userMessage) {
    case '/start':
      bot.sendMessage(
        chatId,
        'Bem-vindo! Use /menu para escolher qual modelo de IA você quer usar.\n' +
        'Suas últimas 10 mensagens serão mantidas como contexto da conversa.'
      );
      return;
    case '/menu':
      showMainMenu(chatId);
      return;
  }

  // If no model is selected, show the menu
  if (!userPreferences.has(chatId)) {
    showMainMenu(chatId);
    return;
  }

  // Send typing action
  bot.sendChatAction(chatId, 'typing');

  // Get response based on selected model
  let response;
  const selectedModel = userPreferences.get(chatId);

  if (selectedModel === 'groq') {
    response = await getGroqChatCompletion(chatId, userMessage);
  } else if (selectedModel === 'azure') {
    response = await getAzureOpenAICompletion(chatId, userMessage);
  } else {
    response = 'Por favor, selecione um modelo usando o /menu primeiro.';
  }

  // Send response back to user
  bot.sendMessage(chatId, response);
});

// Error handling
bot.on('polling_error', (error) => {
  console.error('Erro no polling do Telegram:', error);
});

// Handle process termination
process.on('SIGINT', () => {
  bot.stopPolling();
  process.exit();
});

console.log('Bot está rodando com gerenciamento de contexto...');