from functools import wraps
from flask import redirect, render_template, request, session, jsonify, flash
from email_validator import validate_email, EmailNotValidError
from datetime import date
import json
import os
import smtplib
from email.message import EmailMessage

def check_email(email):
    try:
        valid = validate_email(email)
        
        return True

    except EmailNotValidError as e:
        return False

def send_error(usr):
    error = {}
    error["error"] = usr
    return jsonify(error)

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def required_roles(*roles):
   def wrapper(f):
      @wraps(f)
      def wrapped(*args, **kwargs):
         if session.get("user_id") is None:
            return redirect("/login")

         elif get_current_user_role() not in roles:
            
            return redirect('/notyours')
         
         return f(*args, **kwargs)
      return wrapped
   return wrapper
 
def get_current_user_role():
   return session.get("user_id")[:2]


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=message)

def calculateAge(birth):
    birthDate = date(birth[0], birth[1], birth[2])
    today = date.today()
    age = today.year - birthDate.year - ((today.month, today.day) < (birthDate.month, birthDate.day))
 
    return age

def create_options(usr):
    return {
        "A" : usr[0],
        "B" : usr[1],
        "C" : usr[2],
        "D" : usr[3]
    }

def calculate_total(usr):
    ans = 0
    for i in usr:
        ans += int(i[-1])
    return ans

def decode_options(usr):
    res = json.loads(usr.replace("\'", "\""))
    return res

def generateanswersheet(saved):
    return (saved["position"], saved["answer"])
