# Memo: What Frustrates UK Banking App Customers

21 October 2026 · Brian Tomassoni

## Bottom line

**Question:** what frustrates UK banking app customers most, and which fix would help the most people?

**Answer:** Account freezes. Of 871 reviews about frozen or restricted accounts, 526 are negative (60%), the most of any complaint. Together with customer support friction, they produce about 1,035 negative reviews, more than all other complaint categories combined (about 384).

What would help most customers: clear in-app status updates for restricted accounts, plus a fast route to a person for customers whose accounts are under review.

## Context

The data is 95,677 App Store and Google Play reviews of 10 UK banking apps, August 2025 to August 2026. That covers 4 traditional banks (Barclays, HSBC, Lloyds, NatWest) and 6 NeoBanks or Challenger institutions (Monzo, Revolut, Starling, Wise, Tide, ANNA Money). Each review is scored for sentiment from −1 (most negative) to 1 (most positive).

- **Sentiment:** both groups tracked together at about 0.40 until May 2026. By August 2026, traditional banks had fallen to 0.30, 23% below NeoBanks at 0.39.
- **By app:** HSBC (20.7%) and NatWest (17.9%) have the highest share of negative reviews. Starling has the lowest (7.2%). Tide and ANNA Money are left out of this comparison because they have too few reviews.

## Top three fixes

1. **Restricted accounts: 526 negative of 871 reviews (60%).** Customers can't differentiate a security check from a non-working app feature. Show in the app that a review is under way, how long it usually takes and how to reach someone. Anti-money-laundering rules often prevent a bank explaining *why* an account is restricted, but it can still explain what happens next.
2. **Customer support friction: 509 negative of 1,143 reviews (45%).** Send customers with a restricted account straight to a trained person, and track how long it takes them to reach one.
3. **App bugs and design issues: 293 negative of 717 reviews (41%).** Track complaints for 14 days after each app release against that app's usual level, and roll back a release that causes a clear jump.

Fees and pricing come up often (908 reviews), but only 9% of them are negative, so they are not a priority.

## Caveats

- **The counts are lower bounds.** Only 3.8% of all reviews match a complaint category; 69.5% are general praise and 26.6% are uncategorised. In hand-labelled random samples, about half of the uncategorised reviews had no specific complaint. The rest were a mix of praise and real complaints the keyword rules missed.
- **Reviewers aren't typical customers.** App reviews come mostly from very happy or very unhappy people. They show what frustrates customers, not how many are affected overall.
- **The sentiment model reads words, not intent.** It can miss sarcasm, or score a calmly written complaint as neutral.

## Links

- [Interactive dashboard (Tableau Public)](https://public.tableau.com/app/profile/tomian.sogral/viz/fintech-reviews-app-dashboard/Dashboard)
- [Full method, SQL and Python (GitHub)](https://github.com/tomasb1805/banking-apps-sentiment-scoring)
