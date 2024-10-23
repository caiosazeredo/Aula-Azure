import requests
import threading
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import tkinter as tk
import asyncio
import os

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Definindo as credenciais (use variáveis de ambiente ou um arquivo de configuração seguro)
AZURE_OPENAI_API_URL = ""
AZURE_API_KEY = ""
TELEGRAM_TOKEN = ""

# Função para enviar solicitação para Azure OpenAI
def get_openai_response(user_message):
    headers = {
        'Content-Type': 'application/json',
        'api-key': AZURE_API_KEY
    }
    data = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    response = requests.post(AZURE_OPENAI_API_URL, json=data, headers=headers)

    if response.status_code == 200:
        completion = response.json()
        return completion['choices'][0]['message']['content']
    else:
        logging.error(f"Erro na solicitação: {response.status_code} - {response.text}")
        return "Desculpe, não consegui obter uma resposta no momento."

# Função que será chamada sempre que uma mensagem for recebida
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    bot_response = get_openai_response(user_message)
    await update.message.reply_text(bot_response)

# Função que será chamada quando o comando /start for usado
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Envie uma mensagem e eu responderei.")

def run_bot():
    # Criar e definir um novo loop de eventos para a thread atual
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Comandos básicos
    application.add_handler(CommandHandler("start", start_command))

    # Responder a todas as mensagens de texto
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Executar o bot
    application.run_polling()

def main():
    # Criar a interface gráfica
    root = tk.Tk()
    root.title("Telegram Bot")

    label = tk.Label(root, text="O bot está em execução...")
    label.pack(padx=20, pady=20)

    # Executar o bot em uma thread separada
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # Iniciar o loop principal da interface gráfica
    root.mainloop()

if __name__ == '__main__':
    try:
        # Se estiver usando o Windows, configure a política do loop de eventos
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        main()
    except Exception as e:
        logging.exception("Ocorreu um erro:")
        input("Pressione Enter para sair...")
