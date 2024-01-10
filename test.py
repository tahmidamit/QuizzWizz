import sqlite3
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

con = sqlite3.connect("quizwizz.db")

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

con.row_factory = dict_factory

db = con.cursor()
db.execute("PRAGMA foreign_keys = ON;")



# re = db.execute("INSERT INTO quiz (title, description, duration, no_of_q, belongs_to, set_by, highest_mark, date_created) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", ('cse120', 'This is a test', 15, 20, 1, 2, None, '19/11/23 23:58:56'))
# con.commit()

# db.execute("INSERT INTO users (username, hash, email, date) VALUES(?, ?, ?, ?)", username.strip(), generate_password_hash(password), email.strip(), date)

# db.execute("INSERT INTO teacher (prefix, ta_name, ta_email, ta_dob, ta_phone, ta_init, ta_password, ta_date_created) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", ('ta', 'Tahmid Bin Haque', 'tahmidbinamit@gmail.com', '2022-9-20', '01772488663', 'TBH1', 'amit00', '19/11/23 23:58:56'))
# con.commit()


# db.execute("INSERT INTO student () VALUES(?, ?, ?, ?)", ('st', 'Shahil Islam', 'shahilrs09@gmail.com', '2022-9-20', '01772488663', 'Brac University', 'amit00', '19/11/23 23:58:56'))
# con.commit()

# res = db.execute("SELECT * From student").fetchall()

# abc = db.execute("SELECT ROW_NUMBER(), * From teacher").fetchall()
# a = ['Who is the president of Bangladesh?', 'Seikh', 'Hasina', 'Abul', 'Sakib', 'A', '5']
# print(a[-2])   
# s = db.execute("INSERT INTO subject VALUES (?, ?)", (None, "Physics"))
# con.commit()
# print(db.lastrowid)
# rows = db.execute("SELECT COUNT(quid) as counter FROM question WHERE belongs_to=1").fetchall()
# print(rows)

# s = [(1, 3), (2, 4)]
# b = [(1, 3), (2, 5)]
# s = 1
# st_id = 1
# idx=2
# qid = 2
# ban = sheet = db.execute("SELECT position, answer, marks FROM question WHERE belongs_to=?",(int(qid),)).fetchall()
set_by = 3
st_id = 2
#rows = db.execute("SELECT q.qid, q.title, q.no_of_q, q.total_mark, q.expired, s.sname, COUNT(quiz_history.student_id) FROM (subject s INNER JOIN quiz q ON  q.belongs_to=s.sid)  LEFT JOIN quiz_history ON q.qid=quiz_history.quiz_id WHERE q.set_by=?", (int(set_by),)).fetchall()
#rows = db.execute("SELECT q.title, t.ta_init, q.total_mark, h.obtained_marks, h.quiz_date FROM quiz q, quiz_history h, subject s, teacher t WHERE q.belongs_to=s.sid AND h.quiz_id=q.qid AND h.student_id=?", (int(st_id),)).fetchall()



def send_result(quiz_detail):
    email = os.getenv('gmail')
    password = os.getenv('gmail_pass')
    msg = EmailMessage()
    msg['Subject'] = f"Quizwizz Update on quiz {quiz_detail["title"]}"
    msg['From'] = email
    msg['To'] = quiz_detail["st_email"]
    msg.set_content(f"Your obtained mark on quiz {quiz_detail["title"]} is {quiz_detail["obtained_marks"]}/{quiz_detail["total_mark"]}.\n")

    msg.add_alternative(f"""\
        <!DOCTYPE html>
            <html>
                <body>
                    <h4 style='display: inline;'>Your obtained mark on quiz {quiz_detail["title"]} set by {quiz_detail["ta_init"]} is</h4>
                    <div style='text-align: center;display: inline;'>

                        <h4 style='color:green; display: inline;'> {quiz_detail["obtained_marks"]}/{quiz_detail["total_mark"]} </h4>

                    </div>
                </body>
                <p> Go to the history tab to see the solution of the quiz. </P>
            </html>
        """, subtype='html')


    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:

        smtp.login(email, password)

        smtp.send_message(msg) 

quiz_idx = 2
st_id = 1


print(info)
print(info2)
print(info3)