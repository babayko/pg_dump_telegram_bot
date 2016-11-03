# coding: utf-8
import time

import re

import sys

import datetime
from functools import partial
from threading import Lock

from telebot import TeleBot
from telebot.util import ThreadPool

WAIT_TIME = 9

pending_jobs = {}
pending_jobs_lock = Lock()


class Bot(TeleBot):
    def __init__(self, token, threaded=True, skip_pending=False):
        TeleBot.__init__(self, token, threaded, skip_pending)
        self.worker_pool = ThreadPool(num_threads=4)

    def process_new_messages(self, new_messages):
        result = []
        for new_message in new_messages:
            if new_message.date < time.time() - 180:
                continue
            result.append(new_message)

        if result:
            TeleBot.process_new_messages(self, result)


class Job(object):
    def __init__(self, bot_msg, build_tak):
        self.bot_msg = bot_msg
        self.bot_msg_id = bot_msg.message_id
        self.human_msg_id = bot_msg.reply_to_message.message_id
        self.chat_id = bot_msg.chat.id
        self.build_task = build_tak


class ConstantineIII(object):
    dump_pattern = re.compile('/dump_(\w*)@?')
    cancel_pattern = re.compile('/cancel_(\w*)@?')

    def __init__(self, token, database_url, database_username,
                 database_password, jobs_names, dumps_folder_path):
        self.bot = Bot(token)
        self.database_url = database_url
        self.database_username = database_username
        self.database_password = database_password
        self.jobs_names = jobs_names
        self.dumps_folder_path = dumps_folder_path

    def wake_up(self):
        self.subscription()
        sys.stdout.write('{} Bot running\n'.format(datetime.datetime.now()))
        self.bot.polling(none_stop=True)

    def subscription(self):
        self.bot.message_handler(regexp='/dump_.*')(self.build_handler)
        self.bot.message_handler(regexp='/cancel_.*')(self.cancel_handler)

    def exec_task(self, *args, **kwargs):
        return self.bot._exec_task(*args, **kwargs)

    def build_handler(self, msg):
        result = self.dump_pattern.match(msg.text)
        if result and result.group(1) in self.jobs_names:
            self.dump_job(msg, self.jobs_names[result.group(1)])

    def cancel_handler(self, message):
        result = self.cancel_pattern.match(message.text)
        if not result or not result.group(1).isdigit():
            return

        cancel_msg_id = int(result.group(1))
        with pending_jobs_lock:
            if cancel_msg_id in pending_jobs:
                job = pending_jobs[cancel_msg_id]
                del pending_jobs[cancel_msg_id]
                self.bot.edit_message_text(
                    u'Отменено.', chat_id=job.chat_id,
                    message_id=job.bot_msg_id)

    def dump_job(self, msg, job_name):
        bot_msg = self.bot.reply_to(msg, wait_msg(WAIT_TIME, msg.message_id))
        job = Job(bot_msg, job_name)
        pending_jobs[job.human_msg_id] = job
        self.exec_task(self.countdown_task, job, time.time(), WAIT_TIME - 1)

    def countdown_task(self, job, start, wait_time):
        retry = partial(
            self.exec_task, self.countdown_task, job, start, wait_time)

        if time.time() - start < 0.91:
            return retry()

        if not pending_jobs_lock.acquire(False):
            return retry()

        try:
            if not wait_time:
                if pending_jobs.pop(job.human_msg_id, False):
                    # Add runner here
                    # runner = JobRunner(self, job)
                    # self.exec_task(runner.build)
                    pass
            else:
                cancel = job.human_msg_id not in pending_jobs
                if not cancel:
                    text = wait_msg(wait_time, job.human_msg_id)
                    self.bot.edit_message_text(text, chat_id=job.chat_id,
                                               message_id=job.bot_msg_id)
                    self.exec_task(
                        self.countdown_task, job, time.time(), wait_time - 1)
        finally:
            pending_jobs_lock.release()


def wait_msg(wait_time, msg_id):
    return u'Запущу через {0}. Отменить /cancel_{1}.'.format(wait_time, msg_id)