import requests, psycopg2, os as pd
from psycopg2.extras import execute_values


BASE_API_URL = 'https://www.balldontlie.io'

SEASON_AVERAGES_PATH = '/api/v1/season_averages'
SEASON_AVERAGES_COLUMNS_TO_KEEP = ['player_id', 'games_played', 'season', 'min', 'ftm', 'fgm', 'fg3m', 'dreb', 'oreb', 'ast', 'pf']
SEASON_AVERAGES_COLUMNS_RENAME = {
    'player_id' : 'PlayerID',
    'games_played': 'PartidosJugados',
    'season': 'Temporada',
    'min': 'MinutosPromedio', 
    'ftm': 'Libres',
    'fgm': 'Dobles',
    'fg3m': 'Triples',
    'dreb': 'RebotesDefensivos',
    'oreb': 'RebotesOfensivos',
    'ast' : 'Asistencias',
    'pf' : 'FaltasCometidas'

}

SEASON_AVERAGES_YEAR = 2017
SEASON_AVERAGES_PLAYERS_IDS = [274, 2198, 473, 334, 319, 363, 2206, 159, 6, 184, 1412, 171, 44, 170, 2118] 


REDSHIFT_HOST = 'data-engineer-cluster.cyhh5bfevlmn.us-east-1.redshift.amazonaws.com'
DB_HOST = 'localhost'
DB_PORT = '5439'
DB_DATA_BASE = 'data-engineer-database'
DB_TABLE_NAME = 'average_player_season_stats'
DB_USER = 'guille_shedden_coderhouse'
DB_PWD_PATH = os.path.join(os.path.dirname(__file__), 'pwd_coder.txt')

TYPE_MAP = {'int64': 'INT','int32': 'INT','float64': 'FLOAT','object': 'VARCHAR(50)','bool':'BOOLEAN'}

class SeasonAverages:

    def __init__(self, season, player_id):
        self.endpoint = BASE_API_URL + SEASON_AVERAGES_PATH
        self.payload = {
            'season': season,
            'player_ids[]': player_id
        }

    
    def get_season_averages( self ):
        try:
            
            response = requests.get(self.endpoint, params=self.payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            
            print(f"REQUEST ERROR: {exc}")
            return None


    def process_data (self, season_averages):
        try:
            if 'data' in season_averages:
                data_frame = pd.DataFrame(season_averages['data'])

                data_frame_filtered = data_frame.loc[:, SEASON_AVERAGES_COLUMNS_TO_KEEP]
                data_frame_filtered.rename(columns=SEASON_AVERAGES_COLUMNS_RENAME, inplace=True)
                data_frame_filtered = data_frame_filtered.drop_duplicates()

                return data_frame_filtered
        except KeyError as exc:
            print( f"DATA PROCESSING ERROR: {exc}" )
            return None
    
    
    def db_connect (self):
        with open(DB_PWD_PATH) as f:
            PWD = f.read()
            
            try:
                conn = psycopg2.connect(
                    host = REDSHIFT_HOST,
                    dbname = DB_DATA_BASE,
                    user = DB_USER,
                    password = PWD,
                    port = DB_PORT
                )
                return conn
            except Exception as exc:
                print ("UNABLE TO CONNECT TO DB SERVER.")
                print (exc)
            finally:
                f.close()
    
    def send_data_to_server (self, conn, data_frame, table_name=DB_TABLE_NAME):
        try:
            column_defs = [f"{name} {TYPE_MAP[str(dtype)]}" for name, dtype in zip(data_frame.columns, data_frame.dtypes)]

            cur = conn.cursor()
            cur.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)});")

            values = [tuple(x) for x in data_frame.to_numpy()]

            insert_sql = f"INSERT INTO {table_name} ({', '.join(data_frame.columns)}) VALUES %s"

            cur.execute("BEGIN")
            execute_values(cur, insert_sql, values)
            cur.execute("COMMIT")
            print('PROCESS FINISHED')
        except Exception as exc:
            print(f"ERROR: {exc}")


season_avg_instance = SeasonAverages( SEASON_AVERAGES_YEAR, SEASON_AVERAGES_PLAYERS_IDS )
season_averages = season_avg_instance.get_season_averages()

if season_averages is not None:
    print("SEASON AVERAGES RETRIEVED SUCCESFULLY.")
    
    processed_data = season_avg_instance.process_data( season_averages )
    if processed_data is not None:
        print("DATA PROCESSED SUCCESSFULLY.")
        
        conn = season_avg_instance.db_connect()
        if conn:
            print("CONNECTED TO THE DATABASE SUCCESSFULLY.")
            season_avg_instance.send_data_to_server(conn, processed_data)
    else:
        print("ERROR PROCESSING DATA.")
else:
    print("ERROR RETRIEVING SEASON AVERAGES.")