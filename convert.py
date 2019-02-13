#Converting existing csv file to tinydb
from tinydb import TinyDB
import os, csv

dir_path = os.path.dirname(os.path.realpath(__file__))
db_path = os.path.join(dir_path,"data3.db")
csv_path = os.path.join(dir_path,"voting_data.csv")

def convert():
    db = TinyDB(db_path,'voting')
    if not db.all():
        with open(csv_path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            dates = []
            for row in csv_reader:
                if row[0] not in dates:
                    dates.append(row[0])
                db.insert({"ip":row[1],"vote":row[2],"date":row[0]})
            db_date = db.table('dates')
            for date in dates:
                db_date.insert({"date":date})
    db.close()

if __name__=="__main__":
    convert()
        
        
