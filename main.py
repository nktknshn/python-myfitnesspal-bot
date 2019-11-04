from uuid import uuid4

from telegram import InlineQueryResultArticle, ParseMode, \
    InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram.utils.helpers import escape_markdown
from enum import Enum

import mfp
import logging
from datetime import date
import os


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


login = os.environ['MFP_LOGIN']
password = os.environ['MFP_PASSWORD']
token = os.environ['TGAPP']

client = mfp.ExtendedClient(login, password)

class ChatState(Enum):
    IDLE = 1
    WAITING_FOOD_ID = 2
    WAITING_FOOD_WEIGHT_ID = 3
    WAITING_FOOD_QTY = 4


def get_today():
    return date.today().strftime("%Y-%m-%d")


def get_state(context):
    return context.user_data['state'] if 'state' in context.user_data else ChatState.IDLE


def set_state(context, state: ChatState):
    context.user_data['state'] = state


def process_message_idle(update, context):
    text = update.message.text.lower()

    recent_food = client.get_recent_food()

    matching_foods = []

    for food in recent_food:
        if text in food.name.lower():
            matching_foods.append(food)

    context.user_data['matching_foods'] = matching_foods

    buttons_list = []

    for food in matching_foods:
        buttons_list.append(
            [InlineKeyboardButton(food.name, callback_data=food.id)]
        )

    if len(matching_foods) > 0:
        set_state(context, ChatState.WAITING_FOOD_ID)
        update.message.reply_text(
            "Select food", reply_markup=InlineKeyboardMarkup(buttons_list))
    else:
        update.message.reply_text("not found")


def process_message_qty(update, context):
    qty = int(update.message.text.lower())

    matching_foods = context.user_data['matching_foods']
    selected_food = context.user_data['selected_food']
    selected_weight = context.user_data['selected_weight']

    update.message.reply_text(
        '{} -- {} x {}'.format(selected_food.name, selected_weight.name, qty))

    total, goal, _ = client.add_food(
        get_today(), 3, selected_food.id, selected_weight.id, qty)

    set_state(context, ChatState.IDLE)
    context.user_data.clear()

    update.message.reply_text('{}/{}'.format(total, goal))


def process_message(update, context):
    state = get_state(context)
    if state == ChatState.IDLE:
        process_message_idle(update, context)
    elif state == ChatState.WAITING_FOOD_QTY:
        process_message_qty(update, context)
    else:
        pass


def process_callback_food_id(update, context):
    query = update.callback_query
    selected_id = int(update.callback_query.data)
    matching_foods = context.user_data['matching_foods']

    selected_food = None

    for food in matching_foods:
        if food.id == selected_id:
            selected_food = food

    context.user_data['selected_food'] = selected_food
    set_state(context, ChatState.WAITING_FOOD_WEIGHT_ID)

    query.edit_message_text(
        text="{}".format(selected_food.name))

    buttons = map(lambda w:
                  [InlineKeyboardButton(w.name, callback_data=w.id)], selected_food.weights)

    query.message.reply_text(
        "Select qty", reply_markup=InlineKeyboardMarkup(list(buttons)))


def process_callback_food_weight_id(update, context):
    query = update.callback_query
    selected_weight_id = int(query.data)
    selected_food = context.user_data['selected_food']

    selected_weight = list(filter(lambda w: w.id == int(
        selected_weight_id), selected_food.weights))[0]
    query.edit_message_text(
        text="{}".format(selected_weight.name))

    context.user_data['selected_weight'] = selected_weight

    set_state(context, ChatState.WAITING_FOOD_QTY)

    query.message.reply_text("How much did you eat?")


def process_callback(update, context):
    state = get_state(context)

    if state == ChatState.WAITING_FOOD_ID:
        process_callback_food_id(update, context)

    elif state == ChatState.WAITING_FOOD_WEIGHT_ID:
        process_callback_food_weight_id(update, context)

    else:
        pass


def main():

    updater = Updater(
        token,
        use_context=True,
        request_kwargs={
            'proxy_url': 'socks5://127.0.0.1:9050/'
        })

    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text, process_message))
    dp.add_handler(CallbackQueryHandler(process_callback))

    updater.start_polling()


if __name__ == '__main__':
    main()
