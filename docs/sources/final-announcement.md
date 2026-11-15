Final round at 10:00 CET

Make sure your best version is running before 10:00: whatever your system answers between 10:00 and 12:00 is what gets scored, and right now quite a few teams are not answering (laptops went to sleep overnight? 😴).

Quick checklist: 

* Your recommender is running and answering
* Your laptop won't sleep: plug it in, keep the lid open, disable sleep (or run it in a server)
* Your `.env` still has the right key

 Does the final continue Saturday's state? Yes: it's the same world, still running. Nothing resets at 10:00. 

* Purchases still count. A returning shopper carries everything they bought: in the history, in the store on Saturday (`shop.events`) and through your recommendations (you can see those in your `feedback`). And remember: a shopper who already bought something tends not to want it again.
* Carts don't. `add_to_cart` records are just activity events: there are no pending carts that turn into purchases later.
* The catalog carries on too: products added on Saturday are still there, and stock and price changes keep arriving in `shop.catalog_updates`.


At 10:00, the leaderboard switches to status lights only; the final ranking appears at 12:00. Good luck! 🍀
