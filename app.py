from re import U
import re
from sqlite3 import Row
from turtle import pos, update
from flask import Flask, render_template, redirect, session, request
from flask_session import Session
from cs50 import SQL
from werkzeug.security import check_password_hash, generate_password_hash
import datetime

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///offun.db")

#Defining Error Messages
def error(error_message):
    return render_template("error.html", error_message=error_message)

#For index route (Feed)
@app.route("/")
def index():
    global user_id
    global username
    if not session.get("user_id"):
        return redirect("/login")
    username = session.get("username")
    user_id = session.get("user_id")
    membership = db.execute("SELECT * FROM users WHERE id=?;", user_id)[0]["memberof"]
    membershipList = membership.split(',')
    allFeeds = db.execute("SELECT * FROM posts;")
    return render_template("index.html", username=username, user_id=user_id, allFeeds=allFeeds, membershipList=membershipList)

#For login route
@app.route("/login", methods=["POST", "GET"])
def login():
    #If have not logged in
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        #Error testing
        if not username:
            return error("Username field cannot be empty")
        elif not password:
            return error("Password field cannot be empty")
        rows = db.execute("SELECT * FROM users WHERE username=?", username)
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return error("Incorrect Username or Password")
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]
        return redirect("/")
    #If already logged in
    if session.get("user_id"):
        return redirect("/")
    #If log out is clicked
    return render_template("login.html")

#For logout route
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

#For register route
@app.route("/register", methods=["POST", "GET"])
def register():
    #Upon clicking register
    if request.method == "POST":
        username = request.form.get("username")
        if not username:
            return error("Username field cannot be empty")
        elif not request.form.get("password"):
            return error("Password field cannot be empty")
        elif not request.form.get("rpassword"):
            return error("Reconfirm Password field cannot be empty")
        elif request.form.get("password") != request.form.get("rpassword"):
            return error("Password did not match reconfirmation passowrd")
        passworddb = generate_password_hash(request.form.get("password"))
        try:
            db.execute("INSERT INTO users (username, hash) VALUES(?,?);", username, passworddb)
            return redirect("/")
        except:
            return error("Username already taken.")
    #Bring to register page
    return render_template("register.html")

#Posting new content
@app.route("/newpost", methods = ["POST", "GET"])
def newpost():
    if not session.get("user_id"):
        return redirect("/login")
    username = session.get("username")
    if request.method == "POST":
        user_id = session["user_id"]
        new_post_title = request.form.get("new_post_title")
        new_post_content = request.form.get("new_post_content")
        new_post_time = request.form.get("new_post_time")
        new_post_place = request.form.get("new_post_place")
        new_post_access = request.form.get("new_post_access")
        if not new_post_title:
            return error("Title cannot be empty")
        if new_post_access:
            try:
                groupID = db.execute("SELECT * FROM groups WHERE group_name=?", new_post_access)[0]["group_id"]
            except IndexError:
                return error("This group does not exist")
            membership = db.execute("SELECT * FROM users WHERE id=?;", user_id)[0]["memberof"]
            membershipList = membership.split(',')
            if str(groupID) not in membershipList:
                return error("You do not have access to this group")
            db.execute("INSERT INTO posts (username, userID, post_title, post_content, event_time, event_place, group_access) VALUES(?,?,?,?,?,?,?);", username, user_id, new_post_title, new_post_content, new_post_time, new_post_place, str(groupID))
        else:
            db.execute("INSERT INTO posts (username, userID, post_title, post_content, event_time, event_place) VALUES(?,?,?,?,?,?);", username, user_id, new_post_title, new_post_content, new_post_time, new_post_place)
        return redirect("/")
    return render_template("newpost.html", username=username)

#Creating new group
@app.route("/creategroup", methods = ["POST", "GET"])
def creategroup():
    if not session.get("user_id"):
        return redirect("/login")
    if request.method == "POST":
        user_id = session["user_id"]
        groupname = request.form.get("groupname")
        if not groupname:
            return error("Group name field cannot be empty")
        elif not request.form.get("password"):
            return error("Password field cannot be empty")
        elif not request.form.get("rpassword"):
            return error("Reconfirm Password field cannot be empty")
        elif request.form.get("password") != request.form.get("rpassword"):
            return error("Password did not match reconfirmation passowrd")
        passworddb = generate_password_hash(request.form.get("password"))
        try:
            db.execute("INSERT INTO groups (group_name, password) VALUES(?,?);", groupname, passworddb)
            groupID = db.execute("SELECT * FROM groups WHERE group_name=?", groupname)[0]["group_id"]
            #Add user into the group
            outdatedGroup = db.execute("SELECT * FROM users WHERE id=?", user_id)[0]["memberof"]
            updatedGroup = outdatedGroup + ',' + str(groupID)
            db.execute("UPDATE users SET memberof=? WHERE id=?;", updatedGroup, user_id)
            return redirect("/")
        except:
            return error("Group name already taken")
    return render_template("creategroup.html", username=username)

#Joining new group
@app.route("/joingroup", methods = ["POST", "GET"])
def joingroup():
    if not session.get("user_id"):
        return redirect("/login")
    if request.method == "POST":
        user_id = session["user_id"]
        groupname = request.form.get("groupname")
        password = request.form.get("password")
        #Error testing
        if not groupname:
            return error("Group name field cannot be empty")
        elif not password:
            return error("Password field cannot be empty")
        rows = db.execute("SELECT * FROM groups WHERE group_name=?", groupname)
        if len(rows) != 1:
            return error("Group not found")
        if not check_password_hash(rows[0]["password"], password):
            return error("Incorrect Password")
        groupID = db.execute("SELECT * FROM groups WHERE group_name=?", groupname)[0]["group_id"]
        #Add user into the group
        outdatedGroup = db.execute("SELECT * FROM users WHERE id=?", user_id)[0]["memberof"]
        outdatedGroupList = outdatedGroup.split(',')
        if str(groupID) in outdatedGroupList:
            return error("You have already joined this group")
        else:
            updatedGroup = outdatedGroup + ',' + str(groupID)
        db.execute("UPDATE users SET memberof=? WHERE id=?;", updatedGroup, user_id)
        return redirect("/")
    return render_template("joingroup.html", username=username)


#For settings route
@app.route("/settings")
def settings():
    if not session.get("user_id"):
        return redirect("/login")
    username = session.get("username")
    return render_template("settings.html", username=username)

#For like post
@app.route("/likepost", methods = ["GET"])
def likepost():
    if not session.get("user_id"):
        return redirect("/login")
    user_id = session.get("user_id")
    flaggedPost = request.args.get("likepost")
    #Check if post has already been liked by user
    rows = db.execute("SELECT upvote_count FROM posts WHERE post_id=?", flaggedPost)
    post = db.execute("SELECT * FROM upvotes WHERE postID=? AND userID=?;", flaggedPost, user_id)
    if len(post) == 1:
        updatedUpvotes = rows[0]["upvote_count"] - 1
        db.execute("UPDATE posts SET upvote_count=? WHERE post_id=?;", updatedUpvotes, flaggedPost)
        db.execute("DELETE FROM upvotes WHERE postID=? AND userID=?;", flaggedPost, user_id)
    else:
        updatedUpvotes = rows[0]["upvote_count"] + 1
        db.execute("UPDATE posts SET upvote_count=? WHERE post_id=?;", updatedUpvotes, flaggedPost)
        db.execute("INSERT INTO upvotes (postID, userID) VALUES(?,?);", flaggedPost, user_id)
    return redirect("/")

#To view who liked the posts
@app.route("/mylikes")
def mylikes():
    if not session.get("user_id"):
        return redirect("/login")
    username = session.get("username")
    flaggedPost = request.args.get("mylikes")
    likes = db.execute("SELECT users.username FROM users INNER JOIN upvotes on users.id = upvotes.userID WHERE upvotes.postID=?;", flaggedPost)
    return render_template('wholiked.html', likes=likes, username=username)


#Profile Page
@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect("/login")
    username = session.get("username")
    user_id = session.get("user_id")
    unique_key = session.get("role")
    membership = db.execute("SELECT * FROM users WHERE id=?;", user_id)[0]["memberof"]
    membershipList = membership.split(',')
    groups = []
    for i in membershipList:
        x = db.execute("SELECT * FROM groups WHERE group_id=?;", int(i))
        if len(x) == 0:
            continue
        groups.append(x)
    membership = db.execute("SELECT * FROM users WHERE id=?;", user_id)[0]["memberof"]
    membershipList = membership.split(',')
    allFeeds = db.execute("SELECT * FROM posts;")
    return render_template("profile.html", groupList = groups, user_id=user_id, allFeeds=allFeeds)