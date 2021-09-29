import igraph as ig
import numpy as np
import pickle
import pandas as pd
from tqdm import tqdm
import os
import heapq
import scipy.stats as stats


def build_cpd_df(fp):
    """ Takes 29 separate compound data files and combines them into a single pandas dataframe for ease of access

    Args:
        fp (string): Filepath to SureChemBL data files (assuming G drive goes to jmalloy3 Google Account)

    Returns:
        None - but does write a pickled dataframe to SureChemBL_Patents/Cpd_Data/ directory
    """
    dfs = []
    for f in tqdm(os.listdir(fp)):
        if f.endswith(".txt"):
            dfs.append(pd.read_csv(fp + f, sep="\t", header=0))

    df = pd.concat(dfs, ignore_index=True)
    print(df)
    pickle.dump(df, file=open(fp + "SureChemBL_allCpds.p", "wb"))

    del df


def find_highest_degrees(df, n, start, stop):
    """ Finds the n highest-degree compounds within a specific date range

    Saves various data associated with those n comopunds - smiles, inchi,
    inchikey, degree, preferential attachment value

    Args:
        df (pandas dataframe): dataframe containing all SureChemBL compounds
        n (int): the number of highest-degree compounds to select
        start (int): 1st year of the range
        stop (int): last year of the range
    """
    print("----------", start, stop, "----------")

    #Finding the top 10 preferential attachment compounds (from 1980-1984 as a test)
    full_id_degrees = pickle.load(file=open(
        "G:\\Shared drives\\SureChemBL_Patents\\Degrees\\full_id_degrees_" +
        str(start) + "_" + str(stop) + ".p", "rb"))
    pref_attach_dict = pickle.load(file=open(
        "G:\\Shared drives\\SureChemBL_Patents\\pref_attach_dict_" +
        str(start) + "_" + str(stop) + ".p", "rb"))

    #Find n compounds with largest degree
    highest_degree_cpds = heapq.nlargest(n,
                                         full_id_degrees,
                                         key=full_id_degrees.get)

    highest_degree_cpds_df = df[df["SureChEMBL_ID"].isin(highest_degree_cpds)]

    pref_attach_values = list(pref_attach_dict.values())

    #Extra information to be added to the csv output file
    degrees = []
    pref_attach_highestCpd_values = []
    pref_attach_percentiles = []

    for cpd in tqdm(highest_degree_cpds_df["SureChEMBL_ID"]):
        #Degree of compound
        degrees.append(full_id_degrees[cpd][-1])

        #Preferential attachment value
        pref_attach_highestCpd_values.append(pref_attach_dict[cpd])

        #Percentile of preferential attachment value
        pref_attach_percentiles.append(
            stats.percentileofscore(pref_attach_values, pref_attach_dict[cpd]))

    highest_degree_cpds_df["degree"] = degrees
    highest_degree_cpds_df["pref_attach_value"] = pref_attach_highestCpd_values
    highest_degree_cpds_df["pref_attach_percentile"] = pref_attach_percentiles

    highest_degree_cpds_df.to_csv(
        "G:\\Shared drives\\SureChemBL_Patents\\Cpd_Data/highest_degree_data_" +
        str(start) + "_" + str(stop) + ".csv")

    print()


def find_llanos_cpds(df):
    """ Tests various compounds found in Llanos et al (2019) in SureChemBL data

    Llanos et al used Reaxys data to find the most popular compounds. This checks
    where those compounds appear, if at all, in SureChembL patent data

    Args:
        df (pandas dataframe): dataframe of all SureChemBL chemistry
    """
    cpds_1980_1999_inchi = {
        "acetic anhydride": "InChI=1S/C4H6O3/c1-3(5)7-4(2)6/h1-2H3",
        "methanol": "InChI=1S/CH4O/c1-2/h2H,1H3",
        "methyl iodide": "InChI=1S/CH3I/c1-2/h1H3",
        "diazomethane": "InChI=1S/CH2N2/c1-3-2/h1H2",
        "formaldehyde": "InChI=1S/CH2O/c1-2/h1H2",
        "benzaldehyde": "InChI=1S/C7H6O/c8-6-7-4-2-1-3-5-7/h1-6H",
        "copper(II) oxide": "InChI=1S/Cu.O",
        "ethanol": "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3",
        "benzoyl chloride": "InChI=1S/C7H5ClO/c8-7(9)6-4-2-1-3-5-6/h1-5H",
        "carbon monoxide": "InChI=1S/CO/c1-2"
    }

    for inchi in cpds_1980_1999_inchi.values():
        print(df[df["InChI"] == inchi])


def main():
    data_fp = "G:\\Shared drives\\SureChemBL_Patents\\Cpd_Data\\"
    # build_cpd_df(data_fp) #NOTE: only needs to be run once

    cpd_df = pickle.load(file=open(data_fp + "SureChemBL_allCpds.p", "rb"))

    # ### Statistics over highest degree compounds ###
    # n = 100  #Number of compounds to find
    # for range in [(1980, 1984), (1985, 1989), (1990, 1994), (1995, 1999),
    #               (2000, 2004), (2005, 2009), (2010, 2014), (2015, 2019)]:
    #     find_highest_degrees(cpd_df, n, range[0], range[1])

    ### Testing Llanos et al (2019) compounds ###
    find_llanos_cpds(cpd_df)


if __name__ == "__main__":
    main()
