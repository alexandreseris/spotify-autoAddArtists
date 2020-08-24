import flask

import server.views as views
from server import utils

import param

app = flask.Flask(__name__)
app.config.from_object("config")
app.secret_key = utils.generateRandomString(10)

app.add_url_rule("/favicon.ico", "favicon", views.favicon)
app.add_url_rule("/", "init", views.init)
app.add_url_rule("/" + param.localServerPage, "index", views.index)
app.add_url_rule("/deleteChoices", "deleteChoices", views.deleteChoices, methods=["POST"])
app.add_url_rule("/playlistInput", "playlistInput", views.playlistInput)
app.add_url_rule("/playlistValidate", "playlistValidate", views.playlistValidate, methods=["POST"])
