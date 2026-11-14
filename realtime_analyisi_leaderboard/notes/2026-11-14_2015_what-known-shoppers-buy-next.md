# 14 Nov, 20:15 CET — what known shoppers buy next, and what we still miss

**Question.** Known shoppers are the one place where we are level with the reference instead of ahead. What do
they go on to buy right after we answer them, did we show it, and when we did not — was the signal there?

**Method.** [`next_purchase.py`](../next_purchase.py): every organic purchase (`shop.events`) made within 30
minutes after a request we served since 18:45 CET (the attribute models, v21–v28), matched to the latest such
request. Products the shopper had already bought are set aside (31% of the purchases), because the carousel
does not sell them again. Organic purchases are a proxy for intent, not the carousel's own sales.

## Did we show it?

| Shoppers | Next purchases (not bought before) | In our 10 |
|---|---|---|
| Known, attribute models (tonight) | 850 | **12.5%** |
| Known, rules v4 (13:40–14:10 CET, same method) | 655 | 8.7% |
| New, attribute models (tonight) | 244 | 13.9% |

The four ranker set-ups of tonight are between 10.7% and 14.3% on about 210 purchases each: not distinguishable.

## What the purchased product looked like from the shopper's side (known shoppers, 850 purchases)

**Attributes the shopper likes** (affinity from their 60-day purchases):

| Affinity | Share of the purchases | Of those, shown by us |
|---|---|---|
| over 1.75 | 40.9% | 20.1% |
| 1.25 – 1.75 | 22.1% | 10.1% |
| 1.0 – 1.25 | 13.2% | 10.7% |
| under 1.0 | 23.3% | 2.5% |

**Subcategory and popularity inside it:**

| The product is… | Popularity rank in its subcategory | Share of the purchases | Of those, shown by us |
|---|---|---|---|
| in a subcategory the shopper has bought in | top 3 | 10.5% | 29.2% |
| | 4 – 10 | 15.8% | 17.2% |
| | 11 – 30 | **19.4%** | 10.9% |
| | 31+ | 9.6% | 1.2% |
| in another subcategory | top 3 | 11.9% | 8.9% |
| | 4 – 10 | 9.6% | 6.1% |
| | 11 – 30 | 7.1% | 1.7% |
| | 31+ | 3.9% | 0.0% |

Inside the subcategories a shopper buys in, their purchases are spread over the whole subcategory: ranks 11–30
hold more of them (19.4%) than the top 3 (10.5%). Our lists follow popularity: we show 29% of the top-3
purchases and 11% of the rank 11–30 ones.

**The session says little about a known shopper's next purchase.** It shares 0 / 1 / 2 attributes with the last
viewed product in 77% / 22% / 1% of cases (two random products: about 81% / 18% / 1%), and it is in the last
view's category 19% of the time. The purchase comes a median of 11 minutes after the request.

## The purchases we missed (744)

| What pointed at the product | Share of the misses | Of those, top-10 of their subcategory |
|---|---|---|
| Liked attributes **and** a subcategory they buy in | **34.5%** | 35.8% |
| Only one of the two | 52.6% | 48.1% |
| Neither | 12.9% | 65.6% |

A third of what we miss is a ranking problem: both signals were there, and two thirds of those products sit
below the top 10 of their subcategory.

## The hypothesis this gives, and why it is not yet a finding

For a known shopper, inside the subcategories they buy in, popularity is not what picks the product — the
attributes are. Two independent pieces agree: these organic purchases, and the carousel table of 15:40
(purchases per impression inside a bought subcategory: top-1 0.18%, ranks 2–3 0.13%, 4–10 0.21%, 11+ 0.16% —
flat). The ranker's popularity features (`pop`, `pop_vs_sub`) may be pulling a known shopper's list towards
the best sellers of their subcategories and away from the deeper products that fit their attributes.

Not established: the carousel table was measured on what v4 and v5 chose to show, and the organic stream is
not the carousel. The test is cheap for the session that trains the models: on the held-out live feedback,
known shoppers only, compare the current ranker with one whose popularity features are blanked or shrunk for
products inside a bought subcategory. If the blanked one ranks the bought product higher, it is worth an arm.

## Checked and dropped along the way

"Viewed in the 60 days but never bought" looks strong in the organic stream (a fifth of the purchases) but
sells no better than an unseen product on the carousel (0.044–0.056% against 0.042–0.053% per impression), so
it is not proposed.

## For the final

This concerns shoppers with a purchase history. For shoppers first seen in the final the history is whatever
the live stream gave us; the same reading applies to it, with less to go on.
