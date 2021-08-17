# Discord Webcam Bot

## What does this?
This implementation of a discord bot allows the user the access all webcams that are listed on the following sites:
- bergfex: `www.bergfex.at/<country>/webcams/` with `<country>` from
 ```
 oesterreich, schweiz, deutschland, italien, slovenia, frankreich, nederland, belgie, polska, czechia, slovakia, spanien, kroatien, bosnien-herzegowina, liechtenstein
 ```
- foto-webcam: `https://www.foto-webcam.eu`

The webcams are stored in a database, provided by `webcams.sql`.
PostgreSQL has been used to create the database. \
In `./bot/db.py` you find the method `sql_query()` which executes the SQL queries.
You may have to tweak this method to get it working for you.

## Usage

The bot can be started like a regular discord bot, by inserting your bot token into the `discord.Client.run()` method.
For help in the discord chat, enter `!w` or `!w help`. All relevant info will be displayed. \
As an addition, the bot can execute native SQL by using the command `!wsql <sql_code>`.
However, no DDL or DML statements are allowed and filtered for.