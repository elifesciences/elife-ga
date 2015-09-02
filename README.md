# elife-ga

Example code that talks to Google Analytics to return a list of paths and their 
view counts, figures out the type of page it is looking at (abstract, full text 
or digest) and returns a dictionary of article id's to page type counts.

# installation

    ./install.sh

You will need a `client_secrets.json` file in the source root. Read the [Google
Docs](https://developers.google.com/api-client-library/python/guide/aaa_client_secrets) 
for more information. 

An example has been provided in `client.secrets.example`. You'll need to slot in
your own `client_secret` and `client_id` values.
    
# usage

    source venv/bin/activate
    python mains.py 'ga:12345678'

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


