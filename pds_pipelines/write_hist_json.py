from pds_pipelines.db import db_connect
from pds_pipelines.models import session_scope
from pds_pipelines.config import upc_db, summaries_path
import os
import json
import argparse

query ="""
        SELECT s.instrumentid, s.targetid, s.stat_type, s.starttime, width_bucket(date_part('month', s.starttime), 1, 12, 11) AS month_bucket, width_bucket(s.val, 0 , 360, 20) AS bucket,
    		((width_bucket(s.val, 0 , 360, 20) -1) * 18) ||
    		' - ' ||
    		(width_bucket(s.val, 0 , 360, 20) * 18) ||
    		' degrees' AS bucket_range, count(*) AS total
        INTO TEMP TABLE histogram_summary
        FROM (SELECT t.instrumentid, t.targetid, t.starttime, v.*
        	  FROM search_terms t,
        	  LATERAL (values('solar_longitude', t.solarlongitude),
        					  ('maximumphase', t.maximumphase),
        					  ('minimumphase', t.minimumphase),
        					  ('maximumemission', t.maximumemission),
        					  ('minimumemission', t.minimumemission),
        					  ('maximumincidence', t.maximumincidence),
        					  ('minimumincidence', t.minimumincidence)) v (stat_type, val)) AS s WHERE s.val IS NOT NULL AND s.starttime IS NOT NULL
        GROUP BY s.instrumentid, s.targetid, s.stat_type, bucket, s.starttime, month_bucket
        ORDER BY s.instrumentid, s.targetid, s.stat_type
        """

def main():
    Session, _ = db_connect(upc_db)

    path = summaries_path

    with session_scope(Session) as session:
        print("Creating Hist Table")
        session.execute(query)
        histogram_qobj = session.query("histogram_summary")
        total_rows = session.execute("SELECT count(*) FROM histogram_summary;").first()[0]
        page_number = 0
        number_of_rows_per_page = 200000
        complete_json_output = []
        print("Paging hist results")
        while True:
            lower_bound = page_number*number_of_rows_per_page
            upper_bound = (page_number*number_of_rows_per_page)+number_of_rows_per_page

            if upper_bound > total_rows:
                number_of_rows_per_page = total_rows - lower_bound

            json_query = "with t AS (SELECT * FROM histogram_summary LIMIT {} OFFSET {}) SELECT json_agg(t) FROM t;".format(number_of_rows_per_page, lower_bound)
            output = session.execute(json_query).fetchall()
            complete_json_output.extend([dict(line) for line in output])


            page_number += 1

            if upper_bound > total_rows:
                break

        print("Finished view generation")

    print("Writing Json")
    json_output = json.dumps(complete_json_output)
    with open(path + "histogram_summary.json", "a") as json_file:
        json_file.write(json_output)

if __name__ == "__main__":
    main()
