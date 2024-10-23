import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
import pandas as pd
import io

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Definindo as credenciais diretamente no código
AZURE_OPENAI_API_URL = ""
AZURE_API_KEY = ""
TELEGRAM_TOKEN = ""

# Dicionário para mapear IDs de usuários aos seus DataFrames
user_data = {}

# Função para enviar solicitação para Azure OpenAI
def get_openai_response(user_message):
    headers = {
        'Content-Type': 'application/json',
        'api-key': AZURE_API_KEY
    }
    data_payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7,
        "max_tokens": 150  # Ajuste conforme necessário
    }
    response = requests.post(AZURE_OPENAI_API_URL, json=data_payload, headers=headers)

    if response.status_code == 200:
        completion = response.json()
        return completion['choices'][0]['message']['content']
    else:
        logger.error(f"Erro na solicitação: {response.status_code} - {response.text}")
        return "Desculpe, não consegui obter uma resposta no momento."

# Função para gerar insights a partir dos dados
def generate_insights(user_id):
    data = user_data.get(user_id)
    if data is None:
        return "Desculpe, não consegui encontrar os dados. Por favor, envie um arquivo CSV primeiro."

    try:
        summary = data.describe(include='all').to_string()
        prompt = f"Baseado nos seguintes dados estatísticos:\n{summary}\n\nGere insights relevantes sobre os dados acima."
        return get_openai_response(prompt)
    except Exception as e:
        logger.error(f"Erro ao gerar insights para o usuário {user_id}: {e}")
        return "Desculpe, ocorreu um erro ao gerar insights."

# Função para gerar recomendações a partir dos dados
def generate_recommendations(user_id):
    data = user_data.get(user_id)
    if data is None:
        return "Desculpe, não consegui encontrar os dados. Por favor, envie um arquivo CSV primeiro."

    try:
        summary = data.describe(include='all').to_string()
        prompt = f"Baseado nos seguintes dados estatísticos:\n{summary}\n\nSugira recomendações para melhorar o desempenho da empresa."
        return get_openai_response(prompt)
    except Exception as e:
        logger.error(f"Erro ao gerar recomendações para o usuário {user_id}: {e}")
        return "Desculpe, ocorreu um erro ao gerar recomendações."

# Função que será chamada sempre que o comando /start for usado
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🔍 Gerar Insights", callback_data='insights'),
            InlineKeyboardButton("💡 Gerar Recomendações", callback_data='recommendations'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Olá! Bem-vindo ao Bot de Análise de Dados.\n\n"
        "Para começar, por favor, envie um arquivo CSV com os dados que deseja analisar.",
        reply_markup=reply_markup
    )

# Função que será chamada quando um arquivo for enviado
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    document = update.message.document

    # Verificar se o arquivo é um CSV
    if document.mime_type != 'text/csv':
        await update.message.reply_text("Por favor, envie um arquivo no formato CSV.")
        return

    # Limitar o tamanho do arquivo (exemplo: 5 MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    if document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text("O arquivo é muito grande. Por favor, envie um arquivo CSV com no máximo 5 MB.")
        return

    try:
        # Baixar o arquivo em memória
        file = await document.get_file()
        file_bytes = await file.download_as_bytearray()
        file_stream = io.BytesIO(file_bytes)
        
        # Ler o CSV com pandas
        data = pd.read_csv(file_stream)
        
        # Armazenar o DataFrame no dicionário
        user_data[user_id] = data
        
        # Enviar confirmação e opções
        keyboard = [
            [
                InlineKeyboardButton("🔍 Gerar Insights", callback_data='insights'),
                InlineKeyboardButton("💡 Gerar Recomendações", callback_data='recommendations'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Arquivo CSV recebido com sucesso! Agora, escolha uma opção abaixo para continuar.",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Erro ao processar o CSV enviado pelo usuário {user_id}: {e}")
        await update.message.reply_text("Ocorreu um erro ao processar o arquivo CSV. Por favor, verifique o formato e tente novamente.")

# Função que será chamada sempre que uma mensagem de texto for recebida
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    # Verificar se o usuário já enviou um CSV
    if user_id not in user_data:
        await update.message.reply_text("Por favor, envie um arquivo CSV antes de solicitar insights ou recomendações.")
        return

    # Opcional: Processar a mensagem de texto conforme necessário
    # Neste exemplo, simplesmente responde com a mensagem processada pela API
    bot_response = get_openai_response(user_message)
    await update.message.reply_text(bot_response)

# Função para lidar com as respostas dos botões
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selection = query.data
    user_id = query.from_user.id

    if selection == 'insights':
        await query.edit_message_text(text="Gerando insights... Por favor, aguarde.")
        insights = generate_insights(user_id)
        await query.message.reply_text(insights)
    elif selection == 'recommendations':
        await query.edit_message_text(text="Gerando recomendações... Por favor, aguarde.")
        recommendations = generate_recommendations(user_id)
        await query.message.reply_text(recommendations)
    else:
        await query.message.reply_text("Opção inválida.")

# Função principal para configurar e iniciar o bot
def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Iniciar o bot
    application.run_polling()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.exception("Ocorreu um erro:")
