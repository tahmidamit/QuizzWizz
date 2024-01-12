import sqlite3
from flask import Flask, flash, jsonify, redirect, render_template, session, request
from werkzeug.security import check_password_hash, generate_password_hash
from extra import login_required, check_email, send_error, dict_factory, required_roles, apology, calculateAge, create_options, calculate_total, decode_options, generateanswersheet
from flask_session import Session
from random import randint
from datetime import datetime
from threading import Thread


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.testing = False
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

con = sqlite3.connect("quizwizz.db", check_same_thread=False)
con.row_factory = dict_factory
db = con.cursor()
db.execute("PRAGMA foreign_keys = ON;")



@app.route("/student")
@required_roles("ST")
def red_st():
    user_id = int(session.get("user_id")[2:])
    rows = db.execute("SELECT st_id, st_name, st_email, st_dob, st_phone, st_current_inst, St_date_created FROM student WHERE st_id=?", (user_id,)).fetchall()
    rows[0]["age"] = calculateAge([int(i) for i in rows[0]["st_dob"].split("-")])
    info = db.execute("SELECT quizes, max_ta FROM (SELECT SUM(quizes) as quizes, MAX(ta_count) as max_ta FROM (SELECT COUNT(quiz.qid) as quizes, COUNT(teacher.ta_init) as ta_count FROM quiz_history, teacher, quiz WHERE quiz_history.quiz_id=quiz.qid AND quiz.set_by=teacher.ta_id AND quiz_history.student_id=? GROUP BY teacher.ta_id))", (user_id,)).fetchall()
    max_ta = info[0]["max_ta"]
    info2 = db.execute("SELECT ta_init FROM (SELECT teacher.ta_init,  COUNT(teacher.ta_init) as counter, quiz_history.obtained_marks, quiz.total_mark FROM quiz_history, teacher, quiz WHERE quiz_history.quiz_id=quiz.qid AND quiz.set_by=teacher.ta_id AND quiz_history.student_id=? GROUP BY teacher.ta_id) WHERE counter=?", (user_id, max_ta)).fetchall()
    info3 = db.execute("SELECT AVG(rating) as avg_rating FROM (SELECT quiz.qid, (CAST(quiz_history.obtained_marks AS REAL)/quiz.total_mark)*100 as rating FROM quiz_history, quiz WHERE quiz_history.quiz_id=quiz.qid AND quiz_history.student_id=?)", (user_id,)).fetchall()

    return render_template("home.html", data=rows[0], info1=info[0]["quizes"], info2=info2 , info3=info3)


@app.route("/student/quiz/<quiz_idx>")
@required_roles("ST")
def st_qz_take(quiz_idx):
    if not quiz_idx:
        return apology("Wrong path")
    else:
        if not quiz_idx.isnumeric():
            return apology("wrong path")
        
        rows = db.execute("SELECT q.qid, q.title, q.description, q.duration, q.no_of_q, q.total_mark, q.belongs_to, s.sname, t.ta_init FROM quiz q, subject s, teacher t WHERE q.belongs_to=s.sid AND q.set_by=t.ta_id AND q.qid=?", (int(quiz_idx),)).fetchall()

        if len(rows)==0:
            return apology("Wrong quiz code!")


        return render_template("take_quiz.html", data=rows[0])


@app.route("/student/getquestion")
@required_roles("ST")
def st_get_questions():
    s = request.args.get("qid")
    if not s:
        return apology("Wrong path")
    if not s.isnumeric():
        return apology("Wrong path")
    
    st_id = int(session.get("user_id")[2:])
    ban = db.execute("SELECT * from quiz_history WHERE quiz_id==? AND student_id==?", (int(s), st_id)).fetchall()
    if len(ban)!=0:
        return "<div style='text-align:center;'><h1>You've already taken the quiz</h1></div>"
    

    rows = db.execute("SELECT * FROM question WHERE belongs_to=? ORDER BY position", (int(s),)).fetchall()
    if len(rows)==0:
        return apology("Wong Path")
    
    for i in rows:
        if i["options"]:
            i["options"] = decode_options(i["options"])
    return render_template("questions.html", data=rows)

@app.route("/student/submit_quiz", methods=['POST'])
@required_roles("ST")
def st_submit_questions():
    if request.method=="POST":
        qid = request.form.get("qid")
        comment = request.form.get("comment")
        st_id = int(session.get("user_id")[2:])
        ban = db.execute("SELECT * from quiz_history WHERE quiz_id=? AND student_id=?", (int(qid), st_id)).fetchall()
        if len(ban)!=0:
            return redirect("/student/quizes")

        answers = []

        rows = db.execute("SELECT COUNT(qu.quid) as counter, q.expired, q.total_mark FROM question qu, quiz q WHERE qu.belongs_to=? AND q.qid=qu.belongs_to", (int(qid),)).fetchall()
        for i in range(1, rows[0]["counter"]+1):
            if request.form.get(str(i)):
                s = request.form.get(str(i)).strip().lower()
                answers.append((i, s))
        sheet = db.execute("SELECT position, answer, marks FROM question WHERE belongs_to=?",(int(qid),)).fetchall()
        marks = 0

        for j in sheet:
            if generateanswersheet(j) in answers:
                marks += j["marks"]
        
        date = datetime.now().strftime("%d/%m/%y %H:%M:%S")
        db.execute("INSERT into quiz_history(quiz_id, student_id, obtained_marks, feedback, quiz_date) VALUES (?, ?, ?, ?, ?)", (int(qid), int(st_id), marks, comment, date))
        con.commit()
        
        usr = {
            "mark" : marks,
            "expired" : int(rows[0]["expired"]),
            "total" : rows[0]["total_mark"]
        }
        return render_template("result_uptade.html", data=usr)


@app.route("/student/quizes")
@required_roles("ST")
def st_qz():
    rows =  db.execute("SELECT * FROM subject").fetchall()
    return render_template("show_st_dashboard.html", data=rows)

@app.route('/student/quizes/<variable>', methods=['GET'])
@required_roles("ST")
def quiz_list(variable):
    rows =  db.execute("SELECT * FROM subject").fetchall()
    for i in rows:
        i["sname"] = "".join(i["sname"].split(" ")).lower()
    idx = None
    for j in rows:
        if j["sname"]==variable:
            idx = j["sid"]
    
    st_id = int(session.get("user_id")[2:])
    new_rows = db.execute("SELECT quiz.qid, quiz.title, quiz.duration, quiz.total_mark, quiz.expired, quiz_history.obtained_marks FROM quiz LEFT JOIN quiz_history ON quiz.qid=quiz_history.quiz_id AND quiz_history.student_id=? WHERE quiz.belongs_to=?", (st_id, int(idx),)).fetchall()
    return render_template("show_st_quiz_dashboard.html", data=new_rows)

@app.route("/student/history")
@required_roles("ST")
def st_hs():
    st_id = int(session.get("user_id")[2:])
    rows = db.execute("SELECT q.qid, q.title, t.ta_init, q.total_mark, q.expired, h.obtained_marks, s.sname, h.quiz_date FROM quiz q, quiz_history h, subject s, teacher t WHERE q.belongs_to=s.sid AND h.quiz_id=q.qid AND q.set_by=t.ta_id AND h.student_id=? ORDER BY q.qid DESC", (int(st_id),)).fetchall()
    return render_template("show_st_history.html", data=rows)


@app.route("/student/history/<quiz_idx>")
@required_roles("ST")
def st_hs_solve(quiz_idx):
    if not quiz_idx:
        return apology("Wrong path")
    else:
        if not quiz_idx.isnumeric():
            return apology("wrong path")
        
        rows = db.execute("SELECT q.qid, q.title, q.description, q.duration, q.no_of_q, q.total_mark, q.belongs_to, q.date_created, q.expired, s.sname, t.ta_init FROM quiz q, subject s, teacher t WHERE q.belongs_to=s.sid AND q.set_by=t.ta_id AND q.qid=?", (int(quiz_idx),)).fetchall()

        if len(rows)==0:
            return apology("Wrong quiz code!")
        
        if rows[0]["expired"]==0:
            return apology("This quiz is still active")
        
        questions = db.execute("SELECT * FROM question WHERE belongs_to=? ORDER BY position", (int(quiz_idx),)).fetchall()
        for i in questions:
            if i["options"]:
                i["options"] = decode_options(i["options"])
        
        return render_template("see_quiz_solved_st.html", data=rows[0], ques=questions)
    
@app.route('/student/profile', methods=['GET', 'POST'])
@required_roles("ST")
def edit_profile():
    st_id = int(session.get("user_id")[2:])
    if request.method=="POST":
        username = request.form.get("name")
        email = request.form.get("email")
        dob = request.form.get("dob")
        inst = request.form.get("institute")
        phone = request.form.get("phone")

        if not username:
            return send_error("Must provide name!")

        elif len(username.strip())<4 or len(username.strip())>18:
            return send_error("Name must be between 4 and 18 of length")
        
        if not dob:
            return send_error("Must provide date of birth..!")

        elif not email:
            return send_error("Must provide email..!")

        elif not check_email(email.strip()):
            return send_error("Invalid Email")
        
        elif not inst:
            return send_error("Must provide institute..!")
        
        elif not 6<len(inst)<30:
            return send_error("Must provide valid institute..!")
        
        cur_email = db.execute("SELECT st_email FROM student WHERE st_id = ?", (st_id,)).fetchall()
        if cur_email[0]["st_email"]==email.strip():
            db.execute("UPDATE student SET st_name=?, st_dob=?, st_phone=?, st_current_inst=? WHERE st_id=?", (username.strip().title(), dob, phone, inst.strip(), st_id))
            con.commit()
            return send_error("Updated..!")
        else:
            rows = db.execute("SELECT st_id FROM student WHERE st_email = ?", (email.strip(),)).fetchall()
            if len(rows)!=0:
                return send_error("Another account with this email already exists..!")
            else:
                db.execute("UPDATE student SET st_name=?, st_email=?, st_dob=?, st_phone=?, st_current_inst=? WHERE st_id=?", (username.strip().title(), email.strip(), dob, phone, inst.strip(), st_id))
                con.commit()
                return send_error("Updated..!")
    else:
        rows = db.execute("SELECT * FROM student WHERE st_id=?", (int(st_id),)).fetchall()
        return render_template("edit_profile.html", data=rows[0], role="ST")

@app.route('/student/password', methods=['GET', 'POST'])
@required_roles("ST")
def change_pass_st():
    st_id = int(session.get("user_id")[2:])
    if request.method=="POST":
        old = request.form.get("oldpassword")
        password = request.form.get("password")
        confirm = request.form.get("password2")

        if not old:
            return send_error("Must provide old password..!")

        elif not password:
            return send_error("Must provide new password..!")
        
        elif not confirm:
            return send_error("Must confirm new password")
        
        elif len(password)<8 or len(password) >20:
            return send_error("Invalid Password. Length don't match!")

        rows = db.execute("SELECT st_password FROM student WHERE st_id=?", (st_id,)).fetchall()
        
        if not check_password_hash(rows[0]["st_password"], old):
            return send_error("Wrong old password")
        
        if not confirm or confirm != password:
            return send_error("Passwords don't match..!")
        
        if check_password_hash(rows[0]["st_password"], password):
            return send_error("Didn't really made changes to the password.")
        
        db.execute("UPDATE student SET st_password=? WHERE st_id=?", (generate_password_hash(password), st_id))
        con.commit()
        return send_error("Updated..!")
    else:
        return render_template("change_pass.html", role="ST")

@app.route("/search")
@required_roles("TA", "ST")
def search_quiz():
    query = request.args.get('q')
    if query:
        ans = []
        rows = db.execute("SELECT qid, title FROM quiz WHERE title LIKE ? LIMIT 5", (str(query)+"%",)).fetchall()
        for i in rows:
            ans.append({"value": i["title"], "url": "quiz/"+str(i["qid"])})
        return jsonify(matching_results=ans)


@app.route("/teacher")
@required_roles("TA")
def red_ta():
    user_id = int(session.get("user_id")[2:])
    rows = db.execute("SELECT ta_id, ta_name, ta_email, ta_dob, ta_phone, ta_init, ta_date_created FROM teacher WHERE ta_id=?", (user_id,)).fetchall()
    rows[0]["age"] = calculateAge([int(i) for i in rows[0]["ta_dob"].split("-")])
    info = db.execute("SELECT COUNT(qid) as created, SUM(students) engaged, users FROM (SELECT quiz.qid, COUNT(quiz_history.student_id) as students, COUNT(DISTINCT quiz_history.student_id) as users FROM quiz LEFT JOIN quiz_history ON quiz.qid=quiz_history.quiz_id WHERE quiz.set_by=? GROUP BY quiz.qid)", (user_id,)).fetchall()
    return render_template("home.html", data=rows[0], info=info[0])

@app.route("/teacher/feedbacks")
@required_roles("TA")
def ta_feedbacks():
    set_by = session.get("user_id")[2:]
    rows = db.execute("SELECT quiz.qid, quiz.title, quiz.no_of_q, quiz.total_mark, quiz.expired, subject.sname, COUNT(quiz_history.student_id) as count, MAX(quiz_history.obtained_marks) as max_mark FROM ((quiz INNER JOIN subject ON quiz.belongs_to=subject.sid) LEFT JOIN quiz_history ON quiz_history.quiz_id=quiz.qid) WHERE quiz.set_by=? GROUP BY quiz.qid ORDER BY quiz.qid DESC", (int(set_by),)).fetchall()
    return render_template("show_ta_feedback.html", data=rows)

@app.route("/teacher/feedbacks/<var>")
@required_roles("TA")
def ta_feedbacks_details(var):
    if not var:
        return redirect("/teacher/feedbacks")
    
    quiz_idx = var

    if not quiz_idx.isnumeric():
            return apology("wrong path")
    
    set_by = session.get("user_id")[2:]
    # check = db.execute("SELECT qid FROM quiz WHERE qid=? AND set_by=?", (int(quiz_idx), int(set_by))).fetchall()
    # if len(check)==0:
    #     return apology("Not your quiz")

    rows = db.execute("SELECT s.st_name, st_current_inst, h.obtained_marks, h.feedback, h.quiz_date, q.total_mark FROM quiz_history h, quiz q, student s WHERE h.quiz_id=q.qid AND h.student_id=s.st_id AND q.qid=? AND q.set_by=?", (int(quiz_idx),int(set_by))).fetchall()

    if len(rows)==0:
        return apology("Wrong quiz code!")

    return render_template("show_ta_feedback_detail.html", data=rows)

@app.route('/teacher/profile', methods=['GET', 'POST'])
@required_roles("TA")
def edit_profile_ta():
    ta_id = int(session.get("user_id")[2:])
    if request.method=="POST":
        username = request.form.get("name")
        email = request.form.get("email")
        dob = request.form.get("dob")
        phone = request.form.get("phone")

        if not username:
            return send_error("Must provide name!")

        elif len(username.strip())<4 or len(username.strip())>18:
            return send_error("Name must be between 4 and 18 of length")
        
        if not dob:
            return send_error("Must provide date of birth..!")

        elif not email:
            return send_error("Must provide email..!")

        elif not check_email(email.strip()):
            return send_error("Invalid Email")

        cur_email = db.execute("SELECT ta_email FROM teacher WHERE ta_id = ?", (ta_id,)).fetchall()
        if cur_email[0]["ta_email"]==email.strip():
            db.execute("UPDATE teacher SET ta_name=?, ta_dob=?, ta_phone=? WHERE ta_id=?", (username.strip().title(), dob, phone, ta_id))
            con.commit()
            return send_error("Updated..!")
        else:
            rows = db.execute("SELECT ta_id FROM teacher WHERE ta_email = ?", (email.strip(),)).fetchall()
            if len(rows)!=0:
                return send_error("Another account with this email already exists..!")
            else:
                db.execute("UPDATE teacher SET ta_name=?, ta_email=?, ta_dob=?, ta_phone=? WHERE ta_id=?", (username.strip().title(), email.strip(), dob, phone, ta_id))
                con.commit()
                return send_error("Updated..!")
    else:
        rows = db.execute("SELECT * FROM teacher WHERE ta_id=?", (int(ta_id),)).fetchall()
        return render_template("edit_profile.html", data=rows[0], role="TA")

@app.route('/teacher/password', methods=['GET', 'POST'])
@required_roles("TA")
def change_pass_ta():
    ta_id = int(session.get("user_id")[2:])
    if request.method=="POST":
        old = request.form.get("oldpassword")
        password = request.form.get("password")
        confirm = request.form.get("password2")

        if not old:
            return send_error("Must provide old password..!")

        elif not password:
            return send_error("Must provide new password..!")
        
        elif not confirm:
            return send_error("Must confirm new password")
        
        elif len(password)<8 or len(password) >20:
            return send_error("Invalid Password. Length don't match!")

        rows = db.execute("SELECT ta_password FROM teacher WHERE ta_id=?", (ta_id,)).fetchall()
        
        if not check_password_hash(rows[0]["ta_password"], old):
            return send_error("Wrong old password")
        
        if not confirm or confirm != password:
            return send_error("Passwords don't match..!")
        
        if check_password_hash(rows[0]["ta_password"], password):
            return send_error("Didn't really made changes to the password.")
        
        db.execute("UPDATE teacher SET ta_password=? WHERE ta_id=?", (generate_password_hash(password), ta_id))
        con.commit()
        return send_error("Updated..!")
    else:
        return render_template("change_pass.html", role="TA")


@app.route("/teacher/quiz", methods=["GET", "POST"])
@required_roles("TA")
def ta_qz_show():
    set_by = session.get("user_id")[2:]
    rows = db.execute("SELECT q.qid, q.title, q.no_of_q, q.total_mark, q.expired, q.date_created, s.sname FROM quiz q, subject s WHERE q.set_by=? AND q.belongs_to=s.sid ORDER BY q.qid DESC", (int(set_by),)).fetchall()
    return render_template("show_ta_dashboard.html", data=rows)

@app.route("/teacher/quiz/delete", methods=["POST"])
@required_roles("TA")
def ta_qz_del():
    if request.method=="POST":
        if not request.form.get("idx"):
            return send_error("Nice try")
        
        idx = int(request.form.get("idx"))
        set_by = session.get("user_id")[2:]
        rows = db.execute("SELECT * FROM quiz WHERE qid=? and set_by=?", (idx, int(set_by))).fetchall()
        if len(rows)==0:
            return send_error("You're not the owner. Can't delete.!")
        else:
            db.execute("DELETE FROM quiz WHERE qid=?", (idx,))
            con.commit()
            return send_error("Deleted!")    
        

@app.route("/teacher/quiz/geturl", methods=["GET", "POST"])
@required_roles("TA")
def ta_qz_geturl():
    if request.method=="POST":
        idx = request.form.get("idx")
        print(idx)
        return send_error(f"http://127.0.0.1:5000/student/quiz/{idx}")



@app.route("/teacher/quiz/<quiz_idx>")
@required_roles("TA")
def ta_qz_detail_show(quiz_idx):
    if not quiz_idx:
        return apology("Wrong path")
    else:
        if not quiz_idx.isnumeric():
            return apology("wrong path")
        
        rows = db.execute("SELECT q.qid, q.title, q.description, q.duration, q.no_of_q, q.total_mark, q.belongs_to, q.date_created, q.expired, s.sname, t.ta_init FROM quiz q, subject s, teacher t WHERE q.belongs_to=s.sid AND q.set_by=t.ta_id AND q.qid=?", (int(quiz_idx),)).fetchall()

        if len(rows)==0:
            return apology("Wrong quiz code!")

        questions = db.execute("SELECT * FROM question WHERE belongs_to=? ORDER BY position", (int(quiz_idx),)).fetchall()
        for i in questions:
            if i["options"]:
                i["options"] = decode_options(i["options"])
        
        count = db.execute("SELECT COUNT(student_id) as st FROM quiz_history WHERE quiz_id=?", (int(quiz_idx),)).fetchall()
        return render_template("see_quiz_solved_ta.html", data=rows[0], ques=questions, count=count[0])


@app.route("/teacher/quiz/expire", methods=["GET", "POST"])
@required_roles("TA")
def ta_qz_expire():
    if request.method=="POST":
        if not request.form.get("idx"):
            return send_error("Nice try")
        
        idx = int(request.form.get("idx"))

        set_by = session.get("user_id")[2:]
        rows = db.execute("SELECT * FROM quiz WHERE qid=? and set_by=?", (idx, int(set_by))).fetchall()
        if len(rows)==0:
            return send_error("You're not the owner. Can't Expire.!")
        else:
            db.execute("UPDATE quiz SET expired=1 WHERE qid=?", (idx,))
            con.commit()
            return send_error("Updated!")




@app.route("/teacher/quiz/create", methods=["GET", "POST"])
@required_roles("TA")
def ta_qz():
    if request.method=="POST":
        title = request.form.get("quiz_title")
        description = request.form.get("quiz_descrip")
        subject = request.form.get("subject")
        duration = request.form.get("duration")

        if not title:
            return send_error("Invalid Title")
        
        if not subject:
            return send_error("Choose a subject")

        if duration==None or duration.isnumeric()==False:
            return send_error("Invalid Duration")

        if int(duration)>600:
            return send_error("Invalid Duration")

        counter = int(request.form.get("count"))
        if counter==1:
            return send_error("Please add atleast 3 question")
        
        if counter==2:
            return send_error("Please add atleast 3 question")
        
        if counter==3:
            return send_error("Please add atleast 3 question")
        
        elif counter>30:
            send_error("Can't add more than 30 question")
        
        form_data = []
        no_q = counter-1
        set_by = session.get("user_id")[2:]
        highest_mark = 0
        date = datetime.now().strftime("%d/%m/%y %H:%M:%S")

        for i in range(1, counter):
            form_data.append(request.form.getlist("q"+str(i)))
        total_mark = calculate_total(form_data)
        db.execute("INSERT INTO quiz(title, description, duration, no_of_q, belongs_to, set_by, highest_mark, total_mark, expired, date_created)\
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (title.strip(), description, int(duration), no_q, int(subject), int(set_by), 0, total_mark, 0, date))
        
        con.commit()
        quiz_idx = int(db.lastrowid)


        for i in range(len(form_data)):
            if len(form_data[i])==7:
                question_type = "mcq"
                q_text = form_data[i][0]
                options = create_options(form_data[i][1:5])
                answer = form_data[i][-2]
                mark = form_data[i][-1]
                
                db.execute("INSERT INTO question (belongs_to, text, marks, answer, options, position, question_type) VALUES(?, ?, ?, ?, ?, ?, ?)", \
                           (quiz_idx, q_text.strip(), int(mark), answer.lower(), str(options), i+1, question_type))
                con.commit()
            elif len(form_data[i])==3:
                question_type = "wrt"
                q_text = form_data[i][0]
                answer = form_data[i][-2]
                mark = form_data[i][-1]
                db.execute("INSERT INTO question (belongs_to, text, marks, answer, options, position, question_type) VALUES(?, ?, ?, ?, ?, ?, ?)", \
                           (quiz_idx, q_text.strip(), int(mark), answer.lower(), None, i+1, question_type))
                con.commit()
        
        return send_error("Created..!")
    
    else:
        rows = db.execute("SELECT sid, sname from subject").fetchall()
        return render_template("quiz_set.html", rows=rows)


@app.route("/teacher/history")
@required_roles("TA")
def ta_hs():
    return render_template("home.html")



@app.route("/countmcq")
def count_question_mcq():
    counter = int(request.args.get("count"))
    if counter==None or counter<=30:
        return render_template("quiz_form_mcq.html", count=counter)
    else:
        return render_template("notallowed.html")



@app.route("/countwrt")
def count_question_wrt():
    counter = int(request.args.get("count"))
    if counter==None or counter<=30:
        return render_template("quiz_form_wrt.html", count=counter)
    else:
        return render_template("notallowed.html")


@app.route("/")
def index():
    if session.get("user_id") is None:
        return render_template("index.html")
    else:
        role = session.get("user_id")[:2]
        if role=="TA":
            return redirect("/teacher")
        elif role=="ST":
            return redirect("/student")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("email"):
            flash("Where's the email..?", 'error')
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Where's the password..?", 'error')
            return render_template("login.html")

        elif not request.form.get("role"):
            flash("Where's the role..?", 'error')
            return render_template("login.html")

        elif request.form.get("role") not in ["student", "teacher"]:
            flash("Invalid role.", 'error')
            return render_template("login.html")

        role = request.form.get("role")
        if role=="student":
            rows = db.execute("SELECT st_id, st_password FROM student WHERE st_email = ?", (request.form.get("email"),)).fetchall()
            if len(rows) != 1 or not check_password_hash(rows[0]["st_password"], request.form.get("password")):
                flash("Invalid user or password.", 'error')
                return render_template("login.html")
            
            session["user_id"] = "ST" + str(rows[0]["st_id"])

            
        elif role=="teacher":
            rows = db.execute("SELECT ta_id, ta_password FROM teacher WHERE ta_email = ?", (request.form.get("email"),)).fetchall()
            if len(rows) != 1 or not check_password_hash(rows[0]["ta_password"], request.form.get("password")):
                flash("Invalid user or password.", 'error')
                return render_template("login.html")
            
            session["user_id"] = "TA" + str(rows[0]["ta_id"])


        # Redirect user to home page
        flash("Login successful.!")
        return redirect("/")
        
    else:
        if session.get("user_id") is None:
            return render_template("login.html")
        else:
            return redirect("/")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")



@app.route("/choose")
def choose():
    if session.get("user_id") is None:
        return render_template("choose.html")
    else:
        return redirect("/")


@app.route("/signup_teacher", methods=["GET", "POST"])
def signup_t():
    if request.method=="POST":
        # Validate the user data
        username = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("password2")
        dob = request.form.get("dob")
        phone = request.form.get("phone")

        if not username:
            return send_error("Must provide name!")

        elif len(username.strip())<4 or len(username.strip())>18:
            return send_error("Name must be between 4 and 18 of length")
        
        if not dob:
            return send_error("Must provide date of birth..!")

        elif not email:
            return send_error("Must provide email..!")

        elif not check_email(email.strip()):
            return send_error("Invalid Email")
        
        elif not password:
            return send_error("Must provide password..!")
        
        elif len(password)<8 or len(password) >20:
            return send_error("Invalid Password")

        elif not confirm or confirm != password:
            return send_error("Passwords don't match..!")
        
        # Check if user already exists
        rows = db.execute("SELECT ta_id FROM teacher WHERE ta_email = ?", (email.strip(),)).fetchall()
        if len(rows)!=0:
            return send_error("Email already exists..!")
        
        init = (username[randint(0, len(username))] + username[randint(0, len(username))] + username[randint(0, len(username))] + (str(db.execute("SELECT MAX(ta_id) as init From teacher").fetchall()[0]["init"]+20230))).upper()

        date = datetime.now().strftime("%d/%m/%y %H:%M:%S")
        db.execute("INSERT INTO teacher (ta_name, ta_email, ta_dob, ta_phone, ta_init, ta_password, ta_date_created) VALUES(?, ?, ?, ?, ?, ?, ?)", (username.strip().capitalize(), email.strip(), dob, phone, init, generate_password_hash(password), date))
        con.commit()

        return send_error("Registered..!")
        
    else:
        if session.get("user_id") is None:
            return render_template("signup_teacher.html")

        else:
            return redirect("/")


@app.route("/signup_student", methods=["GET", "POST"])
def signup_s():
    if request.method=="POST":
        # Validate the user data
        username = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("password2")
        dob = request.form.get("dob")
        inst = request.form.get("institute")
        phone = request.form.get("phone")

        if not username:
            return send_error("Must provide name!")

        elif len(username.strip())<4 or len(username.strip())>18:
            return send_error("Name must be between 4 and 18 of length")
        
        if not dob:
            return send_error("Must provide date of birth..!")

        elif not email:
            return send_error("Must provide email..!")

        elif not check_email(email.strip()):
            return send_error("Invalid Email")
        
        elif not inst:
            return send_error("Must provide institute..!")
        
        elif not 6<len(inst)<30:
            return send_error("Must provide valid institute..!")
        
        elif not password:
            return send_error("Must provide password..!")
        
        elif len(password)<8 or len(password) >20:
            return send_error("Invalid Password")

        elif not confirm or confirm != password:
            return send_error("Passwords don't match..!")

        # Check if user already exists
        rows = db.execute("SELECT st_id FROM student WHERE st_email = ?", (email.strip(),)).fetchall()
        if len(rows)!=0:
            return send_error("Email already exists..!")
        
        date = datetime.now().strftime("%d/%m/%y %H:%M:%S")
        db.execute("INSERT INTO student (st_name, st_email, st_dob, st_phone, st_current_inst, st_password, st_date_created) VALUES(?, ?, ?, ?, ?, ?, ?)", (username.strip().capitalize(), email.strip(), dob, phone, inst.strip().capitalize(), generate_password_hash(password), date))
        con.commit()

        return send_error("Registered..!")

    else:
        if session.get("user_id") is None:
            return render_template("signup_student.html")
        else:
            return redirect("/")
    
@app.route("/notyours")
def sendrr():
    if session.get("user_id") is None:
        return redirect("/login")

    usr = session["user_id"][:2]
    if usr=="ST":
        return apology("You're not a Teacher")
    elif usr=="TA":
        return apology("You're not a teacher")
