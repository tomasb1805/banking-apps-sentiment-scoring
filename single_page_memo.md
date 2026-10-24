# Memo: What Frustrates UK Banking App Customers

24 October 2026 · Brian Tomassoni

## Bottom line

**Question:** what frustrates UK banking app customers most, and which fix would help the most people?

**Answer:** Account freezes, and the support customers get once their account is frozen. Of 1,145 reviews about frozen or restricted accounts, 697 are negative (61%), the highest share of any complaint. Customer support friction produces the most negative reviews (742). Together they produce 1,439 negative reviews, more than all other complaint categories combined (1,149).

What would help most customers: clear in-app status updates for restricted accounts, plus a fast route to a person for customers whose accounts are under review.

## Context

The data is 98,292 App Store and Google Play reviews of 10 UK banking apps, August 2025 to August 2026. That covers 4 traditional banks (Barclays, HSBC, Lloyds, NatWest) and 6 NeoBanks or Challenger institutions (Monzo, Revolut, Starling, Wise, Tide, ANNA Money). Each review is scored for sentiment from −1 (most negative) to 1 (most positive).

- **Sentiment:** both groups tracked together at about 0.40 until May 2026. By August 2026, traditional banks had fallen to 0.30, 24% below NeoBanks at 0.39.
- **By app:** HSBC (22.9%) and NatWest (19.5%) have the highest share of negative reviews. Starling has the lowest (8.2%). Tide and ANNA Money are left out of this comparison because they have too few reviews.

## Recommendations

1. **Restricted accounts: 697 negative of 1,145 reviews (61%).** Customers can't differentiate a security check from a non-working app feature. Show in the app that a review is under way, how long it usually takes and how to reach someone. Anti-money-laundering rules often prevent a bank explaining *why* an account is restricted, but it can still explain what happens next.
2. **Customer support friction: 742 negative of 1,794 reviews (41%).** Send customers with a restricted account straight to a trained person, and track how long it takes them to reach one.
3. **App bugs and design issues: 577 negative of 1,328 reviews (43%).** Track complaints for 14 days after each app release against that app's usual level, and roll back a release that causes a clear jump.

Fees and pricing come up often (1,060 reviews), but only 11% of them are negative, so they are not a priority.

## Caveats

- **The counts are lower bounds.** Only 6.4% of all reviews match a complaint category; 67.6% are general praise and 26.0% are uncategorised. In hand-labelled random samples, about half of the uncategorised reviews had no specific complaint. The rest were a mix of praise and real complaints the keyword rules missed.
- **Reviewers aren't typical customers.** App reviews come mostly from very happy or very unhappy people. They show what frustrates customers, not how many are affected overall.
- **The sentiment scoring algorithm reads words, not intent.** It can miss sarcasm, or score a calmly written complaint as neutral.

## Links

- [Interactive dashboard (Tableau Public)](https://public.tableau.com/app/profile/tomian.sogral/viz/fintech-reviews-app-dashboard/Dashboard)
- [Full method, SQL and Python (GitHub)](https://github.com/tomasb1805/banking-apps-sentiment-scoring)
