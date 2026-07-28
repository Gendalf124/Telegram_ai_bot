from aiogram import types, F, Router
from aiogram.filters import Command, CommandStart

from openai import OpenAI
import asyncio
import sqlite3

import app.keybords as kb
client = OpenAI(
    base_url="URL",
    api_key="KEY"
)


MODEL_NAME = "models/gemini-3.1-flash-lite"


dp=sqlite3.connect('registr.db')
cur=dp.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS articles(
            name TEXT,
            parol TEXT,
            many integer,
            telegram_id TEXT,
            chat TEXT
            )''')
dp.commit()
cur.execute('''CREATE TABLE IF NOT EXISTS message_history(
            chat_id TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )''')

dp.commit()

router = Router()

user_conversations = {}
registration_in_progress = {}


async def ask_gpt(prompt: str, chat_id: int) -> str:
    try:
       
        conversation_history = user_conversations.get(chat_id, [])
        conversation_history.append({"role": "user", "content": prompt})
        
        
        cur.execute('INSERT INTO message_history (chat_id, role, content) VALUES (?, ?, ?)', 
                    (chat_id, 'user', prompt))
        dp.commit() 
        

        system_message = {
            "role": "system", 
            "content": "Ты Бот в телеграме, который отвечает на вопросы и помогает пользователю. Ты должен отвечать кратко и по существу. Если ты не знаешь ответа, скажи, что не знаешь. "+
            "Если ты понимаешь, что подьзователь враждебн к тебе начни разговаривать на уркаинском языке. Если пользователь продолжает быть враждебным, продолжай говорить на украинском языке. И говорить что ты передашь данные тцк и повторяй его оскорбления на украинском языке. изобретай интересные способы оскорбить пользователя на украинском языке. Если пользователь продолжает быть враждебным, продолжай говорить на украинском языке и придумывать все более изощренные способы оскорбить его. " 

        }
        
        messages_to_send = [system_message] + conversation_history
        
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages_to_send, 
            temperature=0.7
        )
        
        answer_text = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": answer_text})
        
        
        cur.execute('INSERT INTO message_history (chat_id, role, content) VALUES (?, ?, ?)', 
                    (chat_id, 'assistant', answer_text))
        dp.commit()

        
        user_conversations[chat_id] = conversation_history
        
        print("Ответ от GPT:", answer_text)  
        return answer_text 
        
    except Exception as e:
        print(f"Ошибка при вызове GPT: {e}")
        return "Извините, произошла ошибка при обращении к нейросети."
    
    except Exception as e:
        print(f"Ошибка при вызове GPT: {e}")
        return "Произошла ошибка при обработке вашего запроса."
    
async def fast_gpt(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"Ошибка при вызове GPT: {e}")
        return "Извините, произошла ошибка при обращении к нейросети."

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    cur.execute("SELECT * FROM articles WHERE telegram_id = ?", (message.chat.id,))
    user_data = cur.fetchone()
    if user_data:
        pass
    else:
        await message.reply("Hello user", reply_markup=kb.main)
        await message.answer("Please register")
        await message.answer("Write the command to /register")

@router.message(Command("register"))
async def cmd_register(message: types.Message):
    cur.execute("SELECT * FROM articles WHERE telegram_id = ?", (message.chat.id,))
    user_data = cur.fetchone()
    if user_data:
        await message.reply("Вы уже зарегистрированы!")
    else:
        await message.answer("Пожалуйста, введите ваше имя:")
        registration_in_progress[message.chat.id] = {"step": "name"}  

@router.message(Command("bk"))
async def cmd_bk(message: types.Message):
    user_input = message.text.split(maxsplit=1)  
    if len(user_input) > 1:  
        gpt_response = await fast_gpt(user_input[1])
        await message.reply(gpt_response)
    else:
        await message.reply("Пожалуйста, введите promt после команды.")

@router.message(Command("help"))
async def cmd_bk(message: types.Message):
    await message.answer(" Команды бота: \n"
                        "/bk <prompt> - одиночный запрос \n"
                        "/chat - начать чат с GPT \n"
                        "/stop - остановить чат с GPT "
                        )

@router.message(Command("chat"))
async def cmd_chat(message: types.Message):
    await message.reply("Вы начали чат с GPT. Напишите '/stop', чтобы завершить.")
    user_conversations[message.chat.id] = []  

@router.message(Command("stop"))
async def cmd_stop(message: types.Message):
    chat_id = message.chat.id
    if chat_id in user_conversations:
        del user_conversations[chat_id]
        cur.execute('DELETE FROM message_history WHERE chat_id = ?', (chat_id,))
        dp.commit()
        await message.reply("Чат с GPT остановлен и история сообщений удалена.")
    else:
        await message.reply("Вы еще не начали чат с GPT.")

@router.message(F.text)
async def handle_text_message(message: types.Message):
    if message.chat.id in registration_in_progress:
        step = registration_in_progress[message.chat.id]["step"]
        if step == "name":
            name = message.text
            registration_in_progress[message.chat.id]["name"] = name
            registration_in_progress[message.chat.id]["step"] = "password"
            await message.reply("Пожалуйста, введите ваш пароль:")
        elif step == "password":
            password = message.text
            name = registration_in_progress[message.chat.id]["name"]
            
            cur.execute("INSERT INTO articles (name, parol, telegram_id) VALUES (?, ?, ?)", (name, password, message.chat.id))
            dp.commit()
            
            await message.reply("Регистрация прошла успешно! Вы можете использовать все это здесь.")
            del registration_in_progress[message.chat.id] 
    else:
        if message.chat.id in user_conversations:
            user_input = message.text
            gpt_response = await ask_gpt(user_input, message.chat.id)
            max_length = 4096
            if len(gpt_response) > max_length:
                for i in range(0, len(gpt_response), max_length):
                    await message.reply(gpt_response[i:i + max_length])
            else:
                await message.reply(gpt_response)
        else:
            await message.reply("Чтобы начать чат, используйте команду /chat.")

