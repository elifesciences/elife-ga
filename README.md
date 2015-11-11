# elife-ga-metrics 

Two responsibilities of this code:

1. Talk to Google Analytics and store the raw data returned.

2. Analyse the raw data and then aggregate and filter as necessary.

Provides the interface `core.article_metrics` that returns a dictionary of 
article views and article downloads, keyed by DOI.

# installation

    ./install.sh

## authentication

For fetching fresh data you will need to authenticate against the eLife 
Google Analytics account using OAuth.

This code can be used entirely without the need for authentication, using only 
the raw data in the `outputs/` directory.

To authenticate you will need a `client_secrets.json` file in the source root. 
Read the [official documentation](https://developers.google.com/api-client-library/python/guide/aaa_client_secrets) for more.

An example has been provided in `client.secrets.example`. You'll need to slot in
your own `client_secret` and `client_id` values.
    
# usage

For yesterday's results, use:

    ./run.sh

For daily metrics and a monthly aggregate for the last month, use:

    ./run-bulk.sh

# example

```python
{
 u'e01489': Counter({'full': 21, 'abstract': 0, 'digest': 0}),
 u'e01496': Counter({'abstract': 2, 'full': 0, 'digest': 0}),
 u'e01498': Counter({'full': 2, 'abstract': 0, 'digest': 0}),
 u'e01503': Counter({'full': 8, 'abstract': 2, 'digest': 0}),
 u'e01524': Counter({'full': 3, 'abstract': 0, 'digest': 0}),
 u'e01530': Counter({'full': 5, 'abstract': 2, 'digest': 2}),
 # ...
}
```

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


