import os
import uuid

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_pymongo import PyMongo
from PIL import Image

app = Flask(__name__)
# setting mongodb
app.config["MONGO_URI"] = "mongodb://localhost:27017/myDB"
# setting session secert key
app.config["SECRET_KEY"] = os.urandom(16)
# 設定上傳文件夾
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# 確保上傳文件夾存在
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# 允許的文件類型
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# mongodb init
mongo = PyMongo(app)


# 提供上傳文件的訪問
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# sign in page
@app.route("/", methods=["POST", "GET"])
@app.route("/signin", methods=["POST", "GET"])
def signin():
    if request.method == "POST":
        # get form data
        UserID = request.form["UserID"]
        Password = request.form["Password"]

        # search user from db
        result = mongo.db.user.find_one({"User": UserID})
        if result:
            # get value from result
            userID = result["User"]
            password = result["Password"]
            # check id and pw
            if userID == UserID and password == Password:
                # setting session
                session["UserID"] = UserID
                return redirect(url_for("home"))
            else:
                error = "密碼錯誤！"
                return render_template("signin.html", error=error)
        else:
            error = "找不到使用者 ID: " + UserID
            return render_template("signin.html", error=error)
    else:
        return render_template("signin.html")


# home page,after signin
@app.route("/home")
def home():
    # get user session
    if "UserID" in session:
        UserID = session["UserID"]
        User = mongo.db.user.find_one(
            {"User": UserID}, {"_id": 0, "User": 1, "admin": 1}
        )
        items = list(
            mongo.db.item.find(
                {},
                {
                    "_id": 0,
                    "ItemName": 1,
                    "ItemID": 1,
                    "ItemDesc": 1,
                    "ItemPic": 1,
                    "ItemStorePlace": 1,
                    "ItemType": 1,
                    "ItemOwner": 1,
                    "ItemGetDate": 1,
                },
            )
        )
        return render_template("home.html", User=User, items=items)
    else:
        return redirect(url_for("signin"))


# add item page
@app.route("/additem", methods=["POST", "GET"])
def additem():
    if request.method == "GET":
        if "UserID" in session:
            UserID = session["UserID"]
            User = mongo.db.user.find_one(
                {"User": UserID}, {"_id": 0, "User": 1, "admin": 1}
            )
            result = mongo.db.type.find({}, {"_id": 0, "name": 1})
            return render_template("additem.html", User=User, itemtype=result)
        else:
            return redirect(url_for("home"))
    elif request.method == "POST":
        Item = dict(request.form)

        # 處理照片上傳
        if "ItemPic" in request.files:
            file = request.files["ItemPic"]
            if file and file.filename != "" and allowed_file(file.filename):
                # 生成唯一文件名
                filename = (
                    str(uuid.uuid4()) + "." + file.filename.rsplit(".", 1)[1].lower()
                )
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)

                # 創建縮圖
                try:
                    with Image.open(filepath) as img:
                        # 調整圖片大小為300x300
                        img.thumbnail((300, 300))
                        thumbnail_path = os.path.join(
                            app.config["UPLOAD_FOLDER"], "thumb_" + filename
                        )
                        img.save(thumbnail_path)
                        Item["ItemPic"] = filename
                except Exception as e:
                    print(f"圖片處理錯誤: {e}")
                    Item["ItemPic"] = filename
            else:
                Item["ItemPic"] = ""

        mongo.db.item.insert_one(Item)
        flash("物品新增成功！", "success")
        return redirect(url_for("home"))


# add type page
@app.route("/addtype", methods=["POST", "GET"])
def addtype():
    if request.method == "GET":
        if "UserID" in session:
            UserID = session["UserID"]
            User = mongo.db.user.find_one(
                {"User": UserID}, {"_id": 0, "User": 1, "admin": 1}
            )
            itemtype = mongo.db.type.find({}, {"_id": 0, "name": 1})
            return render_template("addtype.html", User=User, itemtype=itemtype)
        else:
            return redirect(url_for("home"))
    elif request.method == "POST":
        mongo.db.type.insert_one(dict(request.form))
        flash("類型新增成功！", "success")
        return redirect(url_for("addtype"))


# manage item page
@app.route("/manageitem", methods=["POST", "GET"])
def manageitem():
    if request.method == "GET":
        if "UserID" in session:
            UserID = session["UserID"]
            User = mongo.db.user.find_one(
                {"User": UserID}, {"_id": 0, "User": 1, "admin": 1}
            )
            items = list(
                mongo.db.item.find(
                    {},
                    {
                        "_id": 0,
                        "ItemName": 1,
                        "ItemID": 1,
                        "ItemDesc": 1,
                        "ItemPic": 1,
                        "ItemStorePlace": 1,
                        "ItemType": 1,
                        "ItemOwner": 1,
                        "ItemGetDate": 1,
                    },
                )
            )
            return render_template("manageitem.html", User=User, items=items)
        else:
            return redirect(url_for("home"))
    elif request.method == "POST":
        # 處理物品資訊更新
        item_id = request.form.get("item_id")
        new_place = request.form.get("new_place")
        if item_id and new_place:
            mongo.db.item.update_one(
                {"ItemID": item_id}, {"$set": {"ItemStorePlace": new_place}}
            )
            flash("物品位置更新成功！", "success")
        return redirect(url_for("manageitem"))


# edit item page
@app.route("/edititem", methods=["POST", "GET"])
def edititem():
    if request.method == "GET":
        if "UserID" in session:
            UserID = session["UserID"]
            User = mongo.db.user.find_one(
                {"User": UserID}, {"_id": 0, "User": 1, "admin": 1}
            )
            items = []
            for i in mongo.db.item.find(
                {},
                {
                    "_id": 1,
                    "ItemName": 1,
                    "ItemID": 1,
                    "ItemDesc": 1,
                    "ItemState": 1,
                    "ItemPic": 1,
                    "ItemStorePlace": 1,
                    "ItemGetDate": 1,
                    "ItemAge": 1,
                    "ItemOwner": 1,
                    "ItemType": 1,
                },
            ):
                i["_id"] = str(i["_id"])
                items.append(i)
            itemtype = mongo.db.type.find({}, {"_id": 0, "name": 1})
            return render_template(
                "edititem.html", User=User, items=items, itemtype=itemtype
            )
        else:
            return redirect(url_for("home"))
    elif request.method == "POST":
        if request.form["Mode"] == "Clone":
            item = dict(request.form)
            item.pop("Mode")
            item.pop("_id")
            print(item)
            mongo.db.item.insert_one(item)
            flash("物品複製成功！", "success")
        elif request.form["Mode"] == "Edit":
            item = dict(request.form)
            item.pop("Mode")
            print(item)
            mongo.db.item.update_one({"_id": item["_id"]}, {"$set": item})
            flash("物品編輯成功！", "success")
        return redirect(url_for("edititem"))


# 搜尋物品
@app.route("/search", methods=["GET"])
def search():
    if "UserID" in session:
        UserID = session["UserID"]
        User = mongo.db.user.find_one(
            {"User": UserID}, {"_id": 0, "User": 1, "admin": 1}
        )

        query = request.args.get("q", "")
        place = request.args.get("place", "")

        # 建立搜尋條件
        search_filter = {}
        if query:
            search_filter["ItemName"] = {"$regex": query, "$options": "i"}
        if place:
            search_filter["ItemStorePlace"] = {"$regex": place, "$options": "i"}

        items = list(
            mongo.db.item.find(
                search_filter,
                {
                    "_id": 0,
                    "ItemName": 1,
                    "ItemID": 1,
                    "ItemDesc": 1,
                    "ItemPic": 1,
                    "ItemStorePlace": 1,
                    "ItemType": 1,
                    "ItemOwner": 1,
                    "ItemGetDate": 1,
                },
            )
        )

        return render_template(
            "search.html", User=User, items=items, query=query, place=place
        )
    else:
        return redirect(url_for("signin"))


if __name__ == "__main__":
    app.run(debug=True)
