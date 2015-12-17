# elife-ga-metrics

Two responsibilities of this code:

1. Talk to Google Analytics and store the raw data returned.

2. Analyse the raw data and then aggregate and filter as necessary.

Provides `core.article_metrics` that returns a dictionary of article views and 
article downloads, keyed by DOI for a given date range. See See `./run.sh`

Looks like: 

```python
    {'downloads': {u'10.7554/eLife.00012': 1,
                   u'10.7554/eLife.00049': 4,
                   u'10.7554/eLife.00260': 1,           
                   # ... [snip] ...
                   },
               
     'views': {u'10.7554/eLife.00003': Counter({'full': 2, 'abstract': 0, 'digest': 0}),
               u'10.7554/eLife.00005': Counter({'full': 3, 'abstract': 0, 'digest': 0}),
               u'10.7554/eLife.00012': Counter({'full': 2, 'abstract': 1, 'digest': 1}),
               # ... [snip] ...
               }
    }
```

Provides `bulk.article_metrics` that returns a dictionary of daily and monthly
views and downloads, keyed by DOI, for a given date range. See `./run-bulk.sh`

Looks like:

```python
    {'daily': {('2015-11-22', '2015-11-22'): {
                 'downloads': {
                        u'10.7554/eLife.00012': 1,
                        u'10.7554/eLife.00049': 4,
                        u'10.7554/eLife.00260': 1,
                        # ...
                        },
                  'views': {
                        u'10.7554/eLife.00003': Counter({'full': 2, 'abstract': 0, 'digest': 0}),
                        u'10.7554/eLife.00005': Counter({'full': 3, 'abstract': 0, 'digest': 0}),
                        u'10.7554/eLife.00007': Counter({'full': 1, 'abstract': 0, 'digest': 0}),
                        # ...
                        },
                   },
            },
       'monthly': {('2015-11-01', '2015-11-30'): {
                    'downloads': {u'10.7554/eLife.00003': 8,
                                  u'10.7554/eLife.00005': 13,
                                  u'10.7554/eLife.00007': 5,
                                  # ...
                                  },
                     'views': {u'10.7554/eLife.00003': Counter({'full': 44, 'abstract': 1, 'digest': 0}),
                               u'10.7554/eLife.00005': Counter({'full': 157, 'abstract': 6, 'digest': 0}),
                               u'10.7554/eLife.00007': Counter({'full': 36, 'abstract': 5, 'digest': 0}),
                               # ...
                               },
                  }
            }
       }
```                                     

# installation

    $ git clone https://github.com/elifesciences/elife-ga-metrics
    $ ./install.sh

## authentication

For fetching fresh data you will need to authenticate against the eLife 
Google Analytics account using OAuth.

This code can be used *entirely without* the need for authentication, using only 
the raw data in the `outputs/` directory (updated daily).

To authenticate you will need a `client-secrets.json` file in the source root or
at `/etc/elife-ga-metrics/client-secrets.json`.
Read the [official documentation](https://developers.google.com/api-client-library/python/guide/aaa_client_secrets) for more.

The only parameter this application requires is which table to look at, and this
is specified in a `.env` file as `GA_TABLE='ga:12345678'`.

## Copyright & Licence

Copyright 2015 eLife Sciences. Licensed under the [GPLv3](LICENCE.txt)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


