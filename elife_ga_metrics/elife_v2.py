#!/usr/bin/python
# -*- coding: utf-8 -*-

# we can reuse these functions
from elife_ga_metrics import elife_v1
from elife_ga_metrics.elife_v1 import event_counts, event_counts_query

def path_counts_query(table_id, from_date, to_date):
    "returns the raw GA results for PDF downloads between the two given dates"
    original_query = elife_v1.event_counts_query(table_id, from_date, to_date)
    new_query = original_query.copy()

    # pdf, full, abstract, digest
    
    new_query.update({
        'filters': ''

    })
    return new_query


def path_counts(path_count_pairs):
    pass
