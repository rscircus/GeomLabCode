# noxfile.py
import nox

locations = "src", "noxfile.py"

@nox.session(python=["3.7"])
def lint(session):
    args = session.posargs or locations
    session.install("flake8")
    session.run("flake8", *args)
