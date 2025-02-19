# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/vis-02-curtailment.ipynb (unless otherwise specified).

__all__ = ['get_wf_ids', 'flatten_list', 'get_curtailed_wfs_df', 'load_curtailed_wfs',
           'add_next_week_of_data_to_curtailed_wfs']

# Cell
flatten_list = lambda list_: [item for sublist in list_ for item in sublist]

def get_wf_ids(dictionary_url='https://raw.githubusercontent.com/OSUKED/Power-Station-Dictionary/main/data/output/power_stations.csv'):
    df_dictionary = pd.read_csv(dictionary_url)
    wf_ids = flatten_list(df_dictionary.query('fuel_type=="wind"')['sett_bmu_id'].str.split(', ').to_list())

    return wf_ids

# Cell
def get_curtailed_wfs_df(
    api_key: str=None,
    start_date: str = '2020-01-01',
    end_date: str = '2020-01-01 1:30',
    wf_ids: list=None,
    dictionary_url: str='https://raw.githubusercontent.com/OSUKED/Power-Station-Dictionary/main/data/output/power_stations.csv'
):
    if wf_ids is None:
        wf_ids = get_wf_ids(dictionary_url=dictionary_url)

    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date).tz_localize('Europe/London')

    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date).tz_localize('Europe/London')

    client = Client()
    df_detsysprices = client.get_DETSYSPRICES(start_date, end_date)

    df_curtailed_wfs = (df_detsysprices
                        .query('recordType=="BID" & soFlag=="T" & id in @wf_ids')
                        .astype({'bidVolume': float})
                        .groupby(['local_datetime', 'id'])
                        ['bidVolume']
                        .sum()
                        .reset_index()
                        .pivot('local_datetime', 'id', 'bidVolume')
                       )

    df_curtailed_wfs = df_curtailed_wfs.reindex(pd.date_range(min(start_date, df_curtailed_wfs.index.min()),
                                                              max(end_date-pd.Timedelta(minutes=30), df_curtailed_wfs.index.max()),
                                                              tz='Europe/London'))

    df_curtailed_wfs.index.name = 'local_datetime'

    return df_curtailed_wfs

# Cell
def load_curtailed_wfs(
    curtailed_wfs_fp: str='data/curtailed_wfs.csv'
):
    df_curtailed_wfs = pd.read_csv(curtailed_wfs_fp)

    df_curtailed_wfs = df_curtailed_wfs.set_index('local_datetime')
    df_curtailed_wfs.index = pd.to_datetime(df_curtailed_wfs.index, utc=True).tz_convert('Europe/London')

    return df_curtailed_wfs

# Cell
def add_next_week_of_data_to_curtailed_wfs(
    curtailed_wfs_fp: str='data/curtailed_wfs.csv',
    save_data: bool=True,
):
    df_curtailed_wfs = load_curtailed_wfs(curtailed_wfs_fp)
    most_recent_ts = df_curtailed_wfs.index.max()

    start_date = most_recent_ts + pd.Timedelta(minutes=30)
    end_date = start_date + pd.Timedelta(days=7)

    client = Client()
    df_curtailed_wfs_wk = get_curtailed_wfs_df(start_date=start_date, end_date=end_date, wf_ids=wf_ids)

    df_curtailed_wfs = df_curtailed_wfs.append(df_curtailed_wfs_wk)
    df_curtailed_wfs.to_csv(curtailed_wfs_fp)

    return df_curtailed_wfs