from pds_pipelines.db import db_connect
from pds_pipelines.config import upc_db, summaries_path
import os
import json
import argparse

queries = {
    'volume_summary': """
        SELECT d.instrumentid, d.targetid, t.targetname, t.system, i.instrument, i.mission, i.spacecraft, i.displayname,
        count(d.*) as image_count, min(s.starttime) as start_date, max(s.starttime) as stop_date, max(s.processdate) as publish_date, min(s.solarlongitude) as min_solar_longitude, max(s.solarlongitude) as max_solar_longitude, min(s.meangroundresolution) as min_mean_ground_resolution, max(s.meangroundresolution) as max_mean_ground_resolution, min(s.minimumphase) as min_minimum_phase, max(s.minimumphase) as max_minimum_phase, min(s.maximumphase) as min_maximum_phase, max(s.maximumphase) as max_maximum_phase, min(s.minimumincidence) as min_minimum_incidence, max(s.minimumincidence) as max_minimum_incidence, min(s.maximumincidence) as min_maximum_incidence, max(s.maximumincidence) as max_maximum_incidence, min(s.minimumemission) as min_minimum_emission, max(s.minimumemission) as max_minimum_emission, min(s.maximumemission) as min_maximum_emission, max(s.maximumemission) as max_maximumemission
        FROM datafiles d
        JOIN instruments i on (i.instrumentid=d.instrumentid)
        JOIN targets t on (t.targetid=d.targetid)
        JOIN search_terms s on (d.upcid=s.upcid)
        GROUP by d.instrumentid, i.instrument, i.mission, i.spacecraft, d.targetid, t.targetname, t.system, i.displayname
        """,
    # 'band_summary': """
    #     SELECT DISTINCT i.instrumentid, i.instrument, j.jsonkeywords -> 'caminfo' -> 'isislabel' -> 'isiscube' -> 'bandbin' ->> 'filtername' AS filtername,
    #     j.jsonkeywords -> 'caminfo' -> 'isislabel' -> 'isiscube' -> 'bandbin' -> 'center' ->> 0 AS center
    #     FROM instruments i
    #     JOIN datafiles d on (d.instrumentid = i.instrumentid)
    #     JOIN json_keywords j on (d.upcid = j.upcid)
    #     """,
    'target_summary': """
        SELECT d.targetid, count(d.*) as target_count
        FROM datafiles d
        GROUP by d.targetid
        union
        select s.targetid, count(s.*) from search_terms s where s.targetid is null group by s.targetid
        order by targetid
    """
}

def parse_args():
    parser = argparse.ArgumentParser(description='Create view JSONs.')

    parser.add_argument('--path', '-p', dest="path", required=False,
                        help="Enter path - where to write the JSONs.")

    args = parser.parse_args()
    return args


def main(user_args):
    if user_args.path:
        path = user_args.path
    else:
        path = summaries_path

    Session, _ = db_connect(upc_db)
    session = Session()

    for key in queries:
        json_query = "with t AS ({}) SELECT json_agg(t) FROM t;".format(queries[key])
        output = session.execute(json_query)
        print("Finished {} Query".format(key))
        json_output = json.dumps([dict(line) for line in output])

        print("Writing Json for {}".format(key))

        with open(path + key + ".json", "w") as json_file:
            json_file.write(json_output)
        print("Finished view generation for {}".format(key))

if __name__ == "__main__":
    main(parse_args())
