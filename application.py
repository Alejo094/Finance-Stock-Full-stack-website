import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():

    users_cash_track_table = db.execute("SELECT symbol, name, SUM(shares) as totalShares,price,SUM(total) as totalbought FROM users_cash_track WHERE id=:id GROUP BY symbol HAVING SUM(shares) >0",id=session["user_id"] )

    cash_left = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])

    x = db.execute("SELECT stock_boug FROM final_tracker WHERE id=:id",id=session["user_id"])

    y= db.execute("SELECT money_accout FROM final_tracker WHERE id=:id",id=session["user_id"])

    return render_template("index.html",users_cash_track_table=users_cash_track_table, cash_left = cash_left, x=x, y=y)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    symbol= request.form.get("symbol")

    total_stock_boug = 0

    if request.method =="POST":

        stock_info=lookup(symbol)

        if not request.form.get("shares") or not symbol:

            return apology("Please enter value for shares or stock name")
        else:

            try:
                num_shares= int(request.form.get("shares"))

            except ValueError:
                return apology("Please enter a positive integer that is not decimal and not a character",400)

        if stock_info != None and num_shares > 0:

            cash_left= db.execute("SELECT cash FROM users WHERE id=:id",id=session["user_id"])

            x = db.execute("SELECT stock_boug FROM final_tracker WHERE id=:id",id=session["user_id"])

            name_stock= stock_info["name"]

            price_stock =stock_info["price"]

            id=session["user_id"]

            stock_bought = num_shares * price_stock

            total_after_purchase =  cash_left[0]["cash"] - stock_bought

            total_stock_boug =  x[0]["stock_boug"] + stock_bought

            total_money_account =   total_stock_boug + total_after_purchase

            if total_after_purchase < 0:

                return apology("You dont have enough money to buy the total amount of stocks please check your balance!")

            db.execute("UPDATE users SET cash=:total_after_purchase WHERE id=:id",total_after_purchase=total_after_purchase,id=session["user_id"])

            db.execute("INSERT INTO users_cash_track (id,symbol,name,shares,price,total,total_stock_boug,total_after_purchase) VALUES (?,?,?,?,?,?,?,?)",id,symbol,name_stock,num_shares,price_stock,stock_bought,total_stock_boug,total_after_purchase)

            db.execute("UPDATE final_tracker SET stock_boug=:total_stock_boug WHERE id=:id",total_stock_boug=total_stock_boug, id=session["user_id"])

            db.execute("UPDATE final_tracker SET money_accout=:total_money_account WHERE id=:id",total_money_account=total_money_account,id=session["user_id"])

            flash("STOCK BOUGHT!")

            return redirect("/")

        elif not num_shares:

            return apology("The stock that you are trying to search doesnt exist or the number of shares is not bigger than cero please check!", 400)

        else:
            return apology("The stock that you are trying to search doesnt exist or the number of shares is not bigger than cero please check!", 400)

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():

    transactions = db.execute("SELECT symbol, name,shares,price,transac_d FROM users_cash_track WHERE id=:id",id=session["user_id"] )

    for i in range(len(transactions)):
        transactions[i]["price"] = transactions[i]["price"]

        return render_template("history.html",transactions=transactions )


@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")) :
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    symbol= request.form.get("symbol")

    if request.method =="POST":

        stock_info=lookup(symbol)

        if stock_info!= None:

            return render_template("quoted.html",stock_info = stock_info)

        else:
            return apology("The stock that you are trying to search doesnt exist please check the symbol or stock")

    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    user_exist= db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

    if request.method == "POST":

        username = request.form.get("username")

        if not username:
            return apology("You need to provide a username please!",400)

        elif len(user_exist) == 1:
            return apology("Username already exists please create other!",400)

        password = request.form.get("password")

        if not password:
            return apology("You need to provide a password please!",400)

        confirmation = request.form.get("confirmation")

        if not confirmation:
            return apology("You need to confirm the password please!",400)

        if password != confirmation:
            return apology("Passwords dont match please check!",400)

        hash_passw = generate_password_hash(password)

        db.execute("INSERT INTO users (username,hash) VALUES (?,?) ",username,hash_passw)

        stock_boug=0
        money_accout=10000

        db.execute("INSERT INTO final_tracker (stock_boug,money_accout) VALUES (?,?)",stock_boug,money_accout )

    return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    stocks_own = db.execute("SELECT symbol FROM users_cash_track WHERE id=:id GROUP BY symbol HAVING SUM(shares) >0",id=session["user_id"])

    if request.method == "POST":

        symbol=request.form.get("symbol")

        if not symbol:
            return apology("Please check that you provided a stock symbol",400)

        num_shares= request.form.get("shares")

        try:
            num_shares= int(request.form.get("shares")) *(-1)

        except ValueError:
            return apology("Please enter a value that is not decimal and a whole number",400)

        if num_shares >=0:
            return apology("Please check that you provided a positive number",400)

        stock_info=lookup(symbol)

        total_sell = num_shares * stock_info["price"]

        id=session["user_id"]

        name_stock= stock_info["name"]

        price_stock =stock_info["price"]

        stock_bought = num_shares * price_stock

        x = db.execute("SELECT stock_boug FROM final_tracker WHERE id=:id",id=session["user_id"])

        y= db.execute("SELECT money_accout FROM final_tracker WHERE id=:id",id=session["user_id"])

        cash_left = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])

        total_stock_boug =  x[0]["stock_boug"] + stock_bought

        total_after_purchase =  cash_left[0]["cash"] - stock_bought

        stocks_ownN = db.execute("SELECT symbol, SUM(shares) as total1 FROM users_cash_track WHERE id=:id GROUP BY symbol HAVING symbol=:symbol",id=session["user_id"],symbol=request.form.get("symbol"))

        final=stocks_ownN[0]["total1"] + num_shares

        total_money_account =   total_stock_boug + total_after_purchase

        if final >= 0:

            db.execute("UPDATE users SET cash=:total_after_purchase WHERE id=:id",total_after_purchase=total_after_purchase,id=session["user_id"])

            db.execute("INSERT INTO users_cash_track (id,symbol,name,shares,price,total, total_stock_boug,total_after_purchase) VALUES (?,?,?,?,?,?,?,?)",id,symbol,name_stock,num_shares,price_stock,stock_bought,total_stock_boug,total_after_purchase)

            db.execute("UPDATE final_tracker SET stock_boug=:total_stock_boug WHERE id=:id",total_stock_boug=total_stock_boug, id=session["user_id"])

            db.execute("UPDATE final_tracker SET money_accout=:total_money_account WHERE id=:id",total_money_account=total_money_account,id=session["user_id"])

            cash_left = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])

            x = db.execute("SELECT stock_boug FROM final_tracker WHERE id=:id",id=session["user_id"])

            y= db.execute("SELECT money_accout FROM final_tracker WHERE id=:id",id=session["user_id"])

            users_cash_track_table = db.execute("SELECT symbol, name, SUM(shares) as totalShares,price,SUM(total) as totalbought FROM users_cash_track WHERE id=:id GROUP BY symbol HAVING SUM(shares) >0",id=session["user_id"] )

            flash("STOCK SOLD!")

            return render_template("index.html",users_cash_track_table=users_cash_track_table, cash_left = cash_left, x=x, y=y)

        else:
            return apology("You dont own that number of shares of this stock! please check",400)

    return render_template("sell.html", stocks_own= stocks_own)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
