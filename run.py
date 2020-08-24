import os

from server.app import app
import param

os.chdir(os.path.dirname(os.path.realpath(__file__)))

print("starting server on http://" + param.localServerName + ":" + str(param.localServerPort))

test = True

# fix bidon pour reload l'app à la modif sinon ça bug

if test:
    while True:
        try:
            app.run(host=param.localServerName, port=param.localServerPort, debug=True)
        except SystemExit:
            pass
else:
    app.run(host=param.localServerName, port=param.localServerPort, debug=True)

print("done")
