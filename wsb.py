import atexit
import json
import urllib.request

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    jsonify,
    session
)
from flask_api import status
import datetime, time
import csv
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import oauth

log = logging.getLogger('apscheduler.executors.default')
log.setLevel(logging.INFO)  # DEBUG

fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
h = logging.StreamHandler()
h.setFormatter(fmt)
log.addHandler(h)

# Create the application instance
app = Flask(__name__, template_folder="")

app.secret_key = ""
with open("secretkey.txt") as creds:
    app.secret_key = creds.read().replace("\n", '')


# Create a URL route in our application for "/"
@app.route('/')
def home():
    """
    This function just responds to the browser ULR
    localhost:5000/
    :return:        the rendered template 'home.html'
    """
    if is_logged_in():
        my_ip = get_ip()
        if has_voted(my_ip):
            return redirect("/results", code=302)
        else:
            return render_template('index.html')
    else:
        text = '<a href="%s">Authenticate with reddit</a>'
        return render_template('login.html')


@app.route('/getauthurl')
def get_auth_url():
    return oauth.make_authorization_url()


@app.route('/results')
def results():
    my_ip = get_ip()
    # if has_voted(my_ip):
    return render_template('results.html')
    # else:
    #    return redirect("/", code=302)


@app.route('/data')
def data_page():
    return render_template("data.html")


@app.route('/today', methods=['POST', 'GET'])
def today():
    # return today's voting results
    date = get_todays_date()
    return jsonify(get_resuts_by_date(date))


@app.route('/getresults', methods=['POST', 'GET'])
def get_results():
    date = request.args['date']

    return jsonify(get_resuts_by_date(date))


@app.route('/getall', methods=['GET'])
def get_all_results():
    results = []

    csv_name = "voting_data.csv"

    dates = []

    with open(csv_name) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            if not dates.__contains__(row[0]):
                dates.append(row[0])

    for date in dates:
        results.append(get_resuts_by_date(date))

    return jsonify({"data": results, "dates": dates})


@app.route('/voted', methods=['POST', 'GET'])
def voted():
    # using real request IP instead
    my_ip = get_ip()

    if has_voted(my_ip):
        return "True"
    else:
        return "False"


@app.route('/poll', methods=['POST', 'GET'])
def poll():
    vote = request.args['answer']
    # using real request IP instead
    ip = get_ip()

    if ip == "401":
        return str(status.HTTP_401_UNAUTHORIZED)

    # no need to check if ip is valid anymore, but stricter vote check
    if vote not in ["bull", "bear"]:
        return str(status.HTTP_400_BAD_REQUEST)

    date = get_todays_date()

    # ensure client hasn't voted yet
    if not has_voted(ip):
        # ensure date is valid - have gotten spam
        if '/' in date:
            # append to csv
            with open('voting_data.csv', 'a') as fd:
                fd.write(date + "," + ip + "," + vote + '\n')

    return render_template('results.html')


@app.route('/market', methods=['GET'])
def market():
    mkt_data = get_market_data()
    return jsonify(mkt_data)


# checks if vote has been made
def has_voted(ip):

    csv_name = "voting_data.csv"
    votes = {}

    with open(csv_name) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        date = get_todays_date()

        for row in csv_reader:
            if row[0] in votes:
                votes[str(row[0])].append(row[1])
            else:
                votes[str(row[0])] = [row[1]]

        # print(votes)
        if date in votes:
            for my_ip in votes[date]:
                if my_ip == ip:
                    return True

        return False


# gets results by date
def get_resuts_by_date(date):
    csv_name = "voting_data.csv"

    with open(csv_name) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0

        bullCount = 0
        bearCount = 0

        for row in csv_reader:
            if row[0] == date:
                if row[2] == "bull":
                    bullCount += 1
                else:
                    bearCount += 1
        return {"date": date, "bullCount": bullCount, "bearCount": bearCount}


def get_market_data():
    quotes = {}
    csv_name = "market_data.csv"
    with open(csv_name) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            quotes[row[0]] = row[1]
    return quotes


# dynamically gets ip - prevents a 500 being thrown by AWS health checks or on local network
def get_ip():
    """
    my_ip = ""
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        my_ip = str(request.environ['REMOTE_ADDR'])
    else:
        my_ip = str(request.environ['HTTP_X_FORWARDED_FOR'])  # if behind a proxy
    print(my_ip)
    return my_ip
    """
    # if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
    #     return str(request.environ['REMOTE_ADDR'])
    # else:
    return get_username()


# gets username instead of IP
def get_username():
    if 'username' in session:
        return session['username']
    else:
        return "401"


# for job scheduling
scheduler = BackgroundScheduler()


# run this after market hours
def job():
    print("Fetching...")

    todays_date = str(datetime.datetime.now())[:10]
    apiKey = ""
    with open("creds.txt") as creds:
        apiKey = creds.read().replace("\n", '')
    url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=SPY&apikey=" + apiKey

    contents = urllib.request.urlopen(url).read()

    time.sleep(0.1)

    parsed = json.loads(contents)

    time.sleep(0.1)

    parsed = parsed["Time Series (Daily)"]

    offset = 1

    previous_date = str(datetime.datetime.now() - datetime.timedelta(days=1))[:10]
    previous_offset = 1

    while previous_date not in parsed:
        previous_offset += 1
        previous_date = str(datetime.datetime.now() - datetime.timedelta(days=previous_offset))[:10]

    previous_close = 0

    if todays_date in parsed:
        data = parsed[todays_date]
        previous_close = parsed[previous_date]["4. close"]

        mktopen = data["1. open"]
        close = data["4. close"]
        pct = str(float(close) / float(previous_close) - 1)

        fdate = (datetime.datetime.now()).strftime("%m/%d/%Y")

        mkt_data = str(fdate) + "," + str(pct)

    else:
        mkt_data = get_todays_date() + "," + "N/A"

    print(mkt_data)
    # append to csv
    f = open('market_data.csv', 'a')
    f.write(mkt_data + '\n')

    # repeat in 24 hours
    scheduler.add_job(func=job, trigger="date",
                                        run_date=datetime.datetime.now() + datetime.timedelta(days=1, seconds=-0.2))


# fetches today's date via external api to avoid server confusion
def get_todays_date():
    date_url = "http://worldclockapi.com/api/json/est/now"
    contents = json.loads(urllib.request.urlopen(date_url).read())
    date = contents['currentDateTime'][:10]
    date = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%m/%d/%Y")
    return date


# needed for oauth
@app.route('/homepage')
def homepage():
    text = '<a href="%s">Authenticate with reddit</a>'
    return text % oauth.make_authorization_url()


# if user has authenticated
def is_logged_in():
    if "username" in session:
        return True
    else:
        return False


# reddit callback endpoint
@app.route('/reddit_callback')
def reddit_callback():
    error = request.args.get('error', '')
    if error:
        return "Error: " + error
    state = request.args.get('state', '')
    if not oauth.is_valid_state(state):
        # Uh-oh, this request wasn't started by us!
        return status.HTTP_403_FORBIDDEN
    code = request.args.get('code')
    access_token = oauth.get_token(code)
    # Note: In most cases, you'll want to store the access token, in, say,
    # a session for use in other parts of your web app.
    session['username'] = oauth.get_username(access_token)  # set username for session
    return redirect("/", code=302)  # redirect to main voting page


# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    print(get_todays_date())
    scheduler.add_job(func=job, trigger="date", run_date = datetime.datetime.now())
    scheduler.start()

    app.run(debug=False, host='0.0.0.0')

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
