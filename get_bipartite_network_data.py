import igraph as ig
import numpy as np
import pickle
from tqdm import tqdm
import pandas as pd
from itertools import islice
import time
import subprocess


def build_month_list(start, end):
    """ Builds a list of all months in a given range

    Args:
        start (int): year describing the start of the data
        end (int): year describing the end of the data (inclusive)

    Returns:
        list: list of all update months in format "YYYY-MM"
    """
    updates = []
    for year in range(start, end + 1):  # all years through the given end
        for month in range(1, 13):  #include 12 months
            if month < 10:
                updates.append(str(year) + "-0" + str(month))
            else:
                updates.append(str(year) + "-" + str(month))

    return updates


def build_master_cpd_date(updates):
    """ Link compunds with the month it was first found

    Args:
        updates (list): list of all months in a certain range
    """
    fp = "G:/Shared drives/SureChemBL_Patents/"

    master_cpd_date_dict = {}

    #Find all compounds belonging to a specific month
    for update in tqdm(updates):
        cpd_date_dict = pickle.load(
            file=open(fp + "CpdPatentIdsDates/cpd_date_dict_" + update +
                      ".p", "rb"))

        for cpd in cpd_date_dict.keys():
            #If that compound was not present before, add it to the master dictionary
            if cpd not in master_cpd_date_dict:
                master_cpd_date_dict[cpd] = update

    pickle.dump(master_cpd_date_dict,
                file=open(fp + "Cpd_Data/master_cpd_date_dict.p", "wb"))

    #Save this dictionary as a dataframe for later analysis
    df = pd.DataFrame(master_cpd_date_dict.items(), columns=["Cpd", "Month"])
    pickle.dump(df, file=open(fp + "Cpd_Data/master_cpd_date_df.p", "wb"))


def link_ids_cpds(fp):
    """ Links all compound SureChemBL Ids to index numbers in igraph network

    Args:
        fp (string): filepath to Google Drive information

    Returns:
        None, writes a master dataframe containing SureChemBL cpd ids, dates, and indicies to
        /Cpd_Data in GDrive
    """
    cpd_date_df = pickle.load(file=open(fp + "master_cpd_date_df.p", "rb"))
    cpd_ID_index_dict = pickle.load(file=open(fp + "cpd_ID_index_dict.p", "rb"))

    indicies = []
    for index, row in tqdm(cpd_date_df.iterrows(), total=cpd_date_df.shape[0]):
        try:
            indicies.append(cpd_ID_index_dict[row["Cpd"]])
        except:
            indicies.append(-1)

    cpd_date_df["Index"] = indicies
    pickle.dump(cpd_date_df, file=open(fp + "master_cpd_date_index_df.p", "wb"))


def check_indicies(df):
    """ Checks how many dataframe entries have no index in bipartite network

    Only 300k have none (1.59%, that's fine)

    Args:
        df (pandas dataframe): master compound-date-index dataframe
    """
    print("Number of cpds:", len(df))
    print("Number of cpds with no index:", len(df[df["Index"] == -1]))


def get_earlier_cpds(month):
    """ Finds all compounds which were inputted into SureChemBL prior to or equal
    to a given month

    Args:
        month (string): Month, in the form YYYY-MM

    Returns:
        pandas dataframe: dataframe containing SureChemBL patent id, month of
        first entry, and igraph index
    """
    #Read in master compound-date-index dataframe
    agave_fp = "Data/Cpd_Data/master_cpd_date_index_df.p"
    #drive_fp = "G:/Shared drives/SureChemBL_Patents/Cpd_Data/master_cpd_date_index_df.p"
    df = pickle.load(file=open(agave_fp, "rb"))

    print(df.head())

    # #Small dataframe analysis
    # check_indicies(df)

    return df[df["Month"] <= month]


def build_subgraph(G, month):
    """ Builds a cpd-patent bipartite subgraph containing only compounds present
    before or in a given month

    Args:
        G (igraph network): full cpd-patent igraph network
        month (string): month

    Returns:
        None, saves each subgraph to /scratch
    """
    #Find all compounds before the given month
    df = get_earlier_cpds(month)

    #Build subgraph from full igraph subgraph (G.subgraph, include only relevant
    # cpd indicies and ALL PATENTS (to avoid cpd-cpd edges))
    num_cpds = 21641384  #Numbers from cpd/patent id dicts used to build igraph network
    num_patents = 4578946

    #Index list of all compounds present in earlier dates, including all patents
    indicies = df["Index"].tolist() + list(
        np.arange(num_cpds, num_cpds + num_patents, 1))
    #Remove all -1s, not entirely sure what's going on with these
    indicies = [x for x in indicies if x != -1]

    G_sub = G.subgraph(indicies)

    pickle.dump(
        G_sub,
        file=open("/scratch/jmalloy3/Patents/Graphs/cpd_patent_" + month + ".p",
                  "wb"))

    del (G_sub)


def read_graph(update):
    """ Reads a cpd-patent graph in .p format

    Assumes that the data are stored in the /scratch/jmalloy3/Graphs/ directory and in the format
    cpd_patent_<update>.p

    Args:
        fp (string): filepath to a specific cpd-patent graph

    Returns:
        G (igraph object): cpd-patent network pertaining to a specific update
    """
    fp = "/scratch/jmalloy3/cpd_patent_" + update + ".p"
    G = pickle.load(open(fp, "rb"))

    print(ig.summary(G))

    return G


def get_degrees(G):
    """ Finds the degree distribution of a igraph network

    Args:
        G (igraph object): igraph network, contains a variety of data including degrees between nodes

    Returns:
        G.degree (list): list of degrees (in order of igraph vertex index)
    """
    return G.degree()


def get_id_degree(G):
    """ Creates a dictionary of compound ids & associated degrees

    Args:
        G (igraph object): igraph network, contains a variety of data including degrees between nodes

    Returns:
        id_degree_dict (dictionary): Associates SurechemBL compound ids with degree value
    """
    id_degree_dict = dict(zip(G.vs["name"], G.degree()))

    return id_degree_dict


def get_network_stats(updates):
    """Finds basic network statistics SureChemBL cpd-patent graphs in a given range

    Calculates num nodes, num edges, avg degree, max degree,
    avg clustering coefficient, largest connected component size

    Args:
        start (int): year of starting point for analysis
        end (int): year of ending point (inclusive)

    Returns:
        (none): writes a file containing the basic network statistics for each month
                in a given myself
    """
    data = []

    for update in updates:
        subprocess.run([
            "rclone",
            "copy",
            "SureChemBL_Patents:Graphs/cpd_patent_" + update + ".p",
            "/scratch/jmalloy3/",
        ])

        G = read_graph(update)
        network_stats = {}

        start = time.time()
        degrees = get_degrees(G)
        #id_degrees = get_id_degree(G)
        # del (G)
        network_stats["Nodes"] = G.vcount()
        network_stats["Edges"] = G.ecount()
        network_stats["Avg Degree"] = np.mean(degrees)
        network_stats["Max Degree"] = max(degrees)

        print("Time elapsed for degree stats:", time.time() - start)

        network_stats["LCC Size"] = G.clusters().giant().vcount()
        network_stats["Clustering coefficient"] = G.transitivity_undirected()

        print(network_stats)
        print()
        data.append(network_stats)

        print("Time elapsed per graph:", time.time() - start)

        subprocess.run(["rm", "/scratch/jmalloy3/cpd_patent_" + update + ".p"])

        pickle.dump(
            data,
            file=open(
                "/scratch/jmalloy3/Patents/NetworkStats/updated_networkStats.p",
                "wb"))

    #     pickle.dump(degrees,
    #                 file=open(
    #                     "/scratch/jmalloy3/Degrees/Months/degrees_" + update +
    #                     ".p", "wb"))

    #     pickle.dump(id_degrees,
    #                 file=open(
    #                     "/scratch/jmalloy3/Degrees/Months/id_degrees_" +
    #                     update + ".p", "wb"))

    df = pd.DataFrame(data)
    df.to_csv("/scratch/jmalloy3/Patents/NetworkStats/stats_1980_1998.csv")


def main():
    updates = build_month_list(1999, 2020)
    #1: Build subgraphs of patents/compounds present before a specific date

    #1a: Link date of first entry & index of compounds
    #build_master_cpd_date(updates) #NOTE: should only be run once
    #link_ids_cpds("G:/Shared drives/SureChemBL_Patents/Cpd_Data/") #NOTE: should only be run once

    G = pickle.load(file=open("/scratch/jmalloy3/Patents/cpd_patent_G.p", "rb"))

    for month in updates:
        build_subgraph(G, month)

    #2: Network stats over these subgraphs (not immediately necessary)
    # get_network_stats(updates)

    #3: Preferential attachement over compounds

    #4: Track compounds over time


if __name__ == "__main__":
    main()
