from flask import Flask, redirect, render_template, request, url_for, session
from flask_pymongo import PyMongo
import os
app = Flask(__name__)
# setting mongodb
app.config["MONGO_URI"] = "mongodb://localhost:27017/myDB"
# setting session secert key
app.config["SECRET_KEY"] = os.urandom(16)
# mongodb init
mongo = PyMongo(app)

# sign in page
@app.route('/', methods=["POST", "GET"])
@app.route('/signin', methods=["POST", "GET"])
def signin():
    if request.method == "POST":
        # get form data
        UserID = request.form["UserID"]
        Password = request.form["Password"]
        # setting session
        session['UserID'] = UserID
        # search user from db>test
        result = mongo.db.user.find_one({"User": UserID})
        if result:
            # get value from result
            userID = result['User']
            password = result["Password"]
            # check id and pw
            if userID == UserID and password == Password:
                return redirect(url_for("home"))
            elif password != Password:
                error = 'Password Error!'
                return render_template('signin.html', error=error)
            else:
                error = "Can't find User ID: "+UserID
                return render_template('signin.html', error=error)
        else:
            return render_template('signin.html')
    else:
        return render_template('signin.html')

# home page,after signin


@app.route('/home')
def home():
    # get user session
    if 'UserID' in session:
        UserID = session['UserID']
        User = mongo.db.user.find_one({"User": UserID}, {
                                      "_id": 0, "User": 1, "admin": 1})
        items = mongo.db.item.find(
            {}, {"_id": 0, "ItemName": 1,  "ItemID": 1,  "ItemDesc": 1, "ItemState": 1})
        return render_template('home.html', User=User, items=items)
    else:
        return redirect(url_for("signin"))

# add item page


@app.route('/additem', methods=["POST", "GET"])
def additem():
    if request.method == "GET":
        if 'UserID' in session:
            UserID = session['UserID']
            User = mongo.db.user.find_one({"User": UserID}, {
                "_id": 0, "User": 1, "admin": 1})
            result = mongo.db.type.find({}, {"_id": 0, "name": 1})
            return render_template('additem.html', User=User, itemtype=result)
        else:
            return redirect(url_for("home"))
    elif request.method == "POST":
        Item = dict(request.form)
        Item["ItemState"] = "true"
        mongo.db.item.insert_one(Item)
        return redirect(url_for("home"))

# add type page


@app.route('/addtype', methods=["POST", "GET"])
def addtype():
    if request.method == "GET":
        if 'UserID' in session:
            UserID = session['UserID']
            User = mongo.db.user.find_one({"User": UserID}, {
                "_id": 0, "User": 1, "admin": 1})
            itemtype = mongo.db.type.find({}, {"_id": 0, "name": 1})
            return render_template('addtype.html', User=User, itemtype=itemtype)
        else:
            return redirect(url_for("home"))
    elif request.method == "POST":
        mongo.db.type.insert_one(dict(request.form))
        return redirect(url_for("addtype"))

# manage item page
@app.route('/manageitem', methods=["POST", "GET"])
def manageitem():
    if request.method == "GET":
        if 'UserID' in session:
            UserID = session['UserID']
            User = mongo.db.user.find_one({"User": UserID}, {
                "_id": 0, "User": 1, "admin": 1})
            items = mongo.db.item.find(
                {}, {"_id": 0, "ItemName": 1,  "ItemID": 1,  "ItemDesc": 1, "ItemState": 1})
            return render_template('manageitem.html', User=User, items=items)
        else:
            return redirect(url_for("home"))
    elif request.method == "POST":
        # mongo.db.type.insert_one(dict(request.form))
        return redirect(url_for("manageitem"))

# edit item page


@app.route('/edititem', methods=["POST", "GET"])
def edititem():
    if request.method == "GET":
        if 'UserID' in session:
            UserID = session['UserID']
            User = mongo.db.user.find_one({"User": UserID}, {
                "_id": 0, "User": 1, "admin": 1})
            items = []
            for i in mongo.db.item.find({}, {"_id": 1, "ItemName": 1,  "ItemID": 1,  "ItemDesc": 1, "ItemState": 1, "ItemPic": 1, "ItemStorePlace": 1, "ItemGetDate": 1, "ItemAge": 1, "ItemOwner": 1, "ItemType": 1}):
                i['_id'] = str(i['_id'])
                items.append(i)
            itemtype = mongo.db.type.find({}, {"_id": 0, "name": 1})
            return render_template('edititem.html', User=User, items=items, itemtype=itemtype)
        else:
            return redirect(url_for("home"))
    elif request.method == "POST":
        if request.form["Mode"] == 'Clone':
            item = dict(request.form)
            item.pop("Mode")
            item.pop("_id")
            print(item)
            mongo.db.item.insert_one(item)
        elif request.form["Mode"] == 'Edit':
            item = dict(request.form)
            item.pop("Mode")
            print(item)
            mongo.db.item.update_one({"_id": item['_id']}, {"$set": item})
        return redirect(url_for("edititem"))


if __name__ == '__main__':
    app.run(debug=True)
