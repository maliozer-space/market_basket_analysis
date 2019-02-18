# -*- coding: utf-8 -*-
"""
Created on Wed Dec 26 11:52:50 2018

@author: Mehmet Ali Özer
"""
#data_read and frame
import pandas as pd

#calculation
from itertools import combinations, groupby
from collections import Counter

#visualization
import seaborn as sns
from IPython.display import display

#frequency function
def freq(objSeries):
    #pd series already have value_counts() method
    if type(objSeries) == pd.core.series.Series:
        return objSeries.value_counts()
    #pair_items is a list, it is counted by counter and returned a series.
    else: 
        return pd.Series(Counter(objSeries))
    
#combinator function
def get_pairs(ts):
    ts = ts.reset_index().values
    #get 2-k itemsets
    twokitemset = list()
    #lambda x:x[0] return date in ts series, and it allows us to groupby date
    for t_date, basket in groupby(ts, lambda x: x[0]):
        item_list = set()
        for item in basket:
            item_list.add(item[1])
            
            #because of combinator returns a tuple for each combinations, mirror effect is serious problem, (A,B) and (B,A) generate different frequency
            #e.g. ('EPSILON','DELTA') occurs 56 times, ('DELTA','EPSILON') occurs 17 times but actual count is that set of {'EPSILON', 'DELTA'} occurs 73 times.
            #Seperation in frequency cannot be accepted.
            #Although they are not different itemset, different values generated for each sight.
            # so we need alphabetical sorting command, it will work because combinator just follows the place of the item, not item itself.
        for pairs in combinations(sorted(item_list), 2):
            twokitemset.append(pairs)
            return twokitemset

path = "files/spend_item.csv"
df = pd.read_csv(path, sep=",");

#conversion dates column string to date
df['t_date'] = pd.to_datetime(df['t_date'])

#the adverse conditions on my bank-account_transaction dataset may contain same item(place) more than one in same day.
#it means same basket can contain twice or more times the same preferred item
#if we think that a basket is like a set, it should contain one element only once
#because of its effect on frequency, in this scenario, preferability-weight of a place in a same timestamp is omitted.
#I interested on that it is just preferred on that day or not, so duplicates are dropped.

#if t_date, item_code pairs are duplicated, drop the duplicated items except first item, to get first item is inevitable.
#e.g. a day may contain 3 times DELTA, it gets first then drops other two.
df = df.drop_duplicates(keep="first")

#dataframe to series conversion
#now we can use date as index
tseries = df.set_index('t_date')['item_code']
    
day_size = freq(tseries.index).rename("preferred_loc")
print("Total basket number is : {0} ".format(len(day_size)))

#get timestamp of the days which have minimum 2 preferred place.
the_days_we_care = day_size[day_size > 1].index
#pandas select column by condition
tseries = tseries[tseries.index.isin(the_days_we_care)]
print("The eliminated 1-item basket number is : {0} ".format(len(day_size)-len(set(tseries.index))))
print("Remaining basket Number is : {0}".format(len(set(tseries.index))))
item_freq = freq(tseries).rename("occurence")

#get item support bigger than 5

#5 item support threshold means the item preferred at least 5% in remaining day size
items_we_care = item_freq[(item_freq/len(set(tseries.index))) * 100 > 5].index
print("Inspected item size : {0}".format(len(items_we_care)))
#playing with index to filter tseries with items_we_care
tseries = tseries.reset_index()
tseries = tseries.set_index("item_code")

tseries = tseries[tseries.index.isin(items_we_care)]

#make index as date again
tseries = tseries.reset_index()
tseries = tseries.set_index("t_date")["item_code"]

item_info = freq(tseries).to_frame("occurence")
item_info['support'] = (item_info["occurence"] / len(set(tseries.index)))*100

print("Remaining basket number after elimination of items which could not pass threshold : {0} ".format(len(day_size)-len(set(tseries.index))))

#produce 2-itemsets
pair_items = get_pairs(tseries)

pairs_info = freq(pair_items).to_frame("occurence_pairs")
pairs_info['support_pairs'] = pairs_info['occurence_pairs'] / len(set(tseries))

# 1 means the 2-itemsets preferred at least 20 times
pairs_info = pairs_info[pairs_info['support_pairs'] >= 1]

#seperate 2-itemsets as column for each item
pairs_info = pairs_info.reset_index().rename(columns={'level_0': 'place1', 'level_1': 'place2'})

#merge data frames like sql join statement
pairs_info = pairs_info.merge(item_info.rename(columns={'occurence':'sup_countLeft','support':'supportLeft'}), left_on="place1", right_index=True)
pairs_info = pairs_info.merge(item_info.rename(columns={'occurence':'sup_countRight','support':'supportRight'}), left_on="place2", right_index=True)


#confidence(A->B) and confidence(B->A) calculations
#confidence(A->B) supportAB / supportA, if we know the preferability of place A and we want to see what is the possibility to prefer B.
#for vice versa, confidence(B->A)supportAB / supportB
pairs_info['confP1->P2'] = pairs_info['support_pairs'] / pairs_info['supportLeft']
pairs_info['confP2->P1'] = pairs_info['support_pairs'] / pairs_info['supportRight']

#lift calcuation 
pairs_info['lift'] = pairs_info['support_pairs'] / (pairs_info['supportLeft'] * pairs_info['supportRight'])

#visualisation of report | desc order by lift
cm = sns.light_palette("orange", as_cmap=True)
display(pairs_info.sort_values(by=['lift'], ascending=False).style.background_gradient(cmap=cm))

#export as excel | desc order by lift
writer = pd.ExcelWriter('apriori_report.xlsx')
pairs_info.sort_values(by=['lift'], ascending=False).style.background_gradient(cmap=cm).to_excel(writer, 'Sheet1')
writer.save()