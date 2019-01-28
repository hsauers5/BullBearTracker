import atexit
import json
import urllib

from flask import (
    Flask,
    render_template,
    request,
    jsonify
)
import datetime, time
import csv
from apscheduler.schedulers.background import BackgroundScheduler
import logging

log = logging.getLogger('apscheduler.executors.default')
log.setLevel(logging.INFO)  # DEBUG

fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
h = logging.StreamHandler()
h.setFormatter(fmt)
log.addHandler(h)



# Create the application instance
app = Flask(__name__, template_folder="")

# Create a URL route in our application for "/"
@app.route('/')
def home():
    """
    This function just responds to the browser ULR
    localhost:5000/

    :return:        the rendered template 'home.html'
    """
    return render_template('index.html')


@app.route('/results')
def results():
    return render_template('results.html')


@app.route('/today', methods=['POST', 'GET'])
def today():
    # return today's voting results
    return jsonify(get_resuts_by_date(datetime.datetime.now().strftime("%x")))


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
    my_ip = request.args['ip']

    if has_voted(my_ip):
        return "True"
    else:
        return "False"


@app.route('/poll', methods=['POST', 'GET'])
def poll():
    vote = request.args['answer']
    ip = request.args['ip']
    date = datetime.datetime.now().strftime("%x")

    # ensure client hasn't voted yet
    if not has_voted(ip):
        # append to csv
        with open('voting_data.csv', 'a') as fd:
            fd.write(date + "," + ip + "," + vote + '\n')

    return render_template('results.html')


# fetches market data @TODO
def fetch_market_data():

    pass


# checks if vote has been made
def has_voted(ip):

    csv_name = "voting_data.csv"
    votes = {}

    with open(csv_name) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        date = datetime.datetime.now().strftime("%x")

        for row in csv_reader:
            if votes.has_key(row[0]):
                votes[str(row[0])].append(row[1])
            else:
                votes[str(row[0])] = [row[1]]

        # print(votes)
        if votes.has_key(date):
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


# for job scheduling
scheduler = BackgroundScheduler()


# run this after market hours
def job():
    print("Fetching...")

    todays_date = str(datetime.datetime.now())[0:10]

    url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=SPY&apikey=D0PCK93T14WWG2I0"

    contents = urllib.urlopen(url).read()

    time.sleep(0.1)

    parsed = json.loads(contents)

    time.sleep(0.1)

    parsed = parsed["Time Series (Daily)"]

    offset = 0

    """
    while not parsed.has_key(todays_date):
        offset += 1
        todays_date = str(datetime.datetime.now() - datetime.timedelta(days=offset))[0:10]
        print(todays_date)
    """

    if parsed.has_key(todays_date):
        data = parsed[todays_date]

        open = data["1. open"]
        close = data["4. close"]
        pct = str(float(close) / float(open) - 1)

        fdate = (datetime.datetime.now() - datetime.timedelta(days=offset)).strftime("%x")

        mkt_data = str(fdate) + "," + str(pct)

    else:
        mkt_data = datetime.datetime.now().strftime("%x") + "," + "0.00"

    print(mkt_data)
    # append to csv
    f = file('market_data.csv', 'a')
    f.write(mkt_data + '\n')

    # repeat in 24 hours
    scheduler.add_job(func=job, trigger="date",
                                        run_date=datetime.datetime.now() + datetime.timedelta(days=1, seconds=-0.2))


# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    scheduler.add_job(func=job, trigger="date", run_date = datetime.datetime.now())
    scheduler.start()

    app.run(debug=False)

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())