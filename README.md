# Discord Webcam Bot

## What does this?
This discord bot allows the user the access all webcams that are listed on the following sites:
- bergfex: `www.bergfex.at/<country>/webcams/` with `<country>` from
 ```
 oesterreich, schweiz, deutschland, italien, slovenia, frankreich, nederland, belgie, polska, czechia, slovakia, spanien, kroatien, bosnien-herzegowina, liechtenstein
 ```
- foto-webcam: `https://www.foto-webcam.eu`

The webcams are stored in a database, provided in `webcams.psql`.
PostgreSQL has been used to create the database. \
In `./bot/db.py` you will find the method `sql_query()` which executes all SQL queries.
You may have to tweak this method to get it working for you.

The webcam database has also been migrated to MySQL, found in `webcams.mysql`.

## Usage

The bot can be used like a regular discord bot, just by giving your bot token to the `WebcamBot().run(<bot_token>)` method.
For help in the discord chat, enter `!w` or `!w help`. All relevant information will be displayed. \
In addition, the bot can execute native SQL queries by using the command `!wsql <sql_code>`.
However, no DDL or DML statements are allowed and filtered for.