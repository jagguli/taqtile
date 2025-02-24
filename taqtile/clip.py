from __future__ import print_function

import json
import os
import shlex
import subprocess
import logging
from os.path import join

from plumbum import local

from taqtile.themes import dmenu_cmd_args
from taqtile.widgets.obscontrol import obs_pause_recording, obs_resume_recording


use_selection = "CLIPBOARD"
blacklist = []
blacklist_text = "*********"
history_len = 50
previous_clip = None
count_call = 0
history_file = os.path.expanduser(
    join(
        os.environ.get("XDG_RUNTIME_DIR", "~/"), "clipmenu.6.steven/line_cache"
    )
)

from taqtile.log import logger


def is_blacklisted(owner_id):
    from libqtile import hook, xcbq

    if not blacklist:
        return False

    if owner_id in hook.qtile.windows_map:
        owner = hook.qtile.windows_map[owner_id].window
    else:
        owner = xcbq.Window(hook.qtile.conn, owner_id)

    owner_class = owner.get_wm_class()
    if owner_class:
        for wm_class in blacklist:
            if wm_class in owner_class:
                return True


# @hook.subscribe.selection_change
def hook_change(name, selection):
    try:
        global previous_clip
        global count_call
        if name != use_selection:
            return

        if selection["selection"] == previous_clip:
            return

        if is_blacklisted(selection["owner"]):
            text = blacklist_text
        else:
            text = selection["selection"].replace("\n", " ")
            text = text.strip()
        if not text:
            return

        count_call += 1
        previous_clip = text
        logger.error("count_call %s" % count_call)
        history = []
        if os.path.isfile(history_file):
            with open(history_file, "r") as qfile:
                history = json.load(qfile)
        if text in history:
            history.remove(text)
        history.append(text)
        with open(history_file, "w+") as qfile:
            json.dump(history, qfile)
    except Exception as e:
        logger.exception("Error getting selection")


def copy_xclip(text, primary=False):
    PRIMARY_SELECTION = "-p"
    DEFAULT_SELECTION = "c"
    ENCODING = "utf-8"
    selection = DEFAULT_SELECTION
    if primary:
        selection = PRIMARY_SELECTION
    p = subprocess.Popen(
        ["xclip", "-selection", selection],
        stdin=subprocess.PIPE,
        close_fds=True,
    )
    p.communicate(input=text.encode(ENCODING))


def dmenu_xclip(qtile, output_clip=False):
    logger.exception("Error getting selection %s", output_clip)
    try:
        obs_pause_recording()
        if output_clip:
            local.env["CM_OUTPUT_CLIP"] = "1"
        clipmenu = local["clipmenu"]
        output = clipmenu("-c", "-i", "-p", "Clipmenu")
        if output_clip:
            local["xdotool"]("type", output)
    finally:
        obs_resume_recording()
