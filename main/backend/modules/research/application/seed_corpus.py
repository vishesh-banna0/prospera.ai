"""Starter corpus for the research knowledge base.

The RAG layer works but ships empty, which makes retrieval look broken on a
fresh install: ``/research/search`` returns nothing until somebody ingests
documents. This module holds a small, curated corpus so the reasoning layer
has real evidence to cite from the very first query.

Two kinds of passage, both chosen because they generalize:

  * Historical market events — how markets actually behaved through the 2008
    crisis, the COVID crash, oil shocks, rate cycles and currency crises.
    These give the reasoner precedent to compare a live event against.
  * Investing principles — mean reversion, drawdown mathematics, position
    sizing, diversification limits. These give it the vocabulary to justify a
    recommendation in terms an investor recognizes.

Everything here is general market history and textbook finance, written for
this repo. It is not investment advice and contains no proprietary research.

Load it with ``python scripts/seed_research.py``. Re-running is safe:
ingestion is keyed on a content hash, so unchanged passages replace
themselves instead of duplicating.
"""

from __future__ import annotations

from backend.modules.research.application.dto import IngestDocumentRequest

SEED_CORPUS: tuple[IngestDocumentRequest, ...] = (
    # --- Historical market events ------------------------------------------
    IngestDocumentRequest(
        title="2008 Global Financial Crisis: Drawdown and Recovery",
        content=(
            "The 2008 global financial crisis began in the US subprime mortgage "
            "market and spread through the banking system via securitized credit "
            "products. The S&P 500 fell roughly 57 percent from its October 2007 "
            "peak to its March 2009 trough. Financials led the decline; consumer "
            "staples, utilities and gold held up far better than the index. "
            "Recovery to the prior peak took about four years. The lesson most "
            "often drawn is that a solvency crisis in the banking system "
            "transmits to every sector through credit availability, so sector "
            "diversification alone does not protect a portfolio in a systemic "
            "event. Investors who continued periodic contributions through the "
            "drawdown recovered materially faster than those who stopped, "
            "because contributions during the decline bought units cheaply."
        ),
        document_type="research_report",
        source="seed:market-history",
        sectors=("Financials",),
    ),
    IngestDocumentRequest(
        title="COVID-19 Crash of 2020: Speed of Decline and Policy Response",
        content=(
            "In February and March 2020 global equities fell roughly 34 percent "
            "in about 23 trading days, the fastest bear market on record. Unlike "
            "2008, the shock was exogenous — a pandemic and the resulting "
            "lockdowns — rather than a failure inside the financial system. "
            "Central banks cut rates to near zero and launched large asset "
            "purchase programs within weeks, and fiscal support followed. "
            "Markets recovered their prior highs within roughly five months. "
            "Airlines, hospitality and energy suffered lasting damage while "
            "software, e-commerce and semiconductors gained. The episode is the "
            "clearest modern example of a transient external shock: the "
            "aggregate index recovered quickly, but the sector composition of "
            "the recovery differed sharply from the composition of the decline."
        ),
        document_type="research_report",
        source="seed:market-history",
        sectors=("Technology", "Energy"),
    ),
    IngestDocumentRequest(
        title="Oil Supply Shocks and Sector Rotation",
        content=(
            "Oil supply shocks — the 1973 embargo, the 1990 Gulf War, the 2022 "
            "invasion of Ukraine — share a recognizable pattern in equity "
            "markets. Energy producers and oilfield services rally on higher "
            "realized prices. Airlines, logistics, paints, chemicals, tyres and "
            "other heavy fuel consumers fall as input costs rise faster than "
            "they can be passed to customers. Broad indices usually fall because "
            "higher energy prices act as a tax on consumption. For import-"
            "dependent economies such as India, a sustained rise in crude also "
            "widens the current account deficit and pressures the currency, "
            "which compounds the effect on importers. The rotation typically "
            "unwinds when supply normalizes, so the energy gain is generally a "
            "trade rather than a long-term holding thesis."
        ),
        document_type="research_report",
        source="seed:market-history",
        sectors=("Energy",),
    ),
    IngestDocumentRequest(
        title="Rate Hiking Cycles and Equity Sector Sensitivity",
        content=(
            "Rising policy rates raise the discount rate applied to future cash "
            "flows, which mechanically hurts long-duration assets — high-growth "
            "companies whose earnings sit far in the future — more than "
            "companies earning cash today. In the 2022 cycle the US Federal "
            "Reserve raised rates from near zero to above 5 percent and "
            "unprofitable technology names fell far more than the index. Banks "
            "often benefit early in a hiking cycle as net interest margins "
            "expand, then suffer later if higher rates cause credit losses or "
            "deposit flight. Utilities and real estate, which are valued partly "
            "against bond yields and often carry leverage, typically "
            "underperform. Rate expectations, not the level of rates, drive most "
            "of the equity market reaction."
        ),
        document_type="research_report",
        source="seed:market-history",
        sectors=("Financials", "Technology"),
    ),
    IngestDocumentRequest(
        title="Indian Market Episodes: Demonetisation, IL&FS and the 2013 Taper Tantrum",
        content=(
            "India's 2016 demonetisation withdrew high-value currency notes "
            "overnight, hurting cash-intensive sectors such as real estate, "
            "jewellery and unorganised retail while accelerating adoption of "
            "digital payments. The 2018 IL&FS default triggered a funding "
            "squeeze across non-banking financial companies, showing how a "
            "single credit event can reprice an entire sector's cost of capital. "
            "During the 2013 taper tantrum the rupee fell sharply against the "
            "dollar as foreign investors withdrew from emerging markets; "
            "IT services exporters, who earn in dollars, benefited while "
            "importers and companies with unhedged foreign debt suffered. Each "
            "episode illustrates that in an emerging market, currency and "
            "funding conditions transmit macro shocks into equity prices as "
            "forcefully as earnings do."
        ),
        document_type="research_report",
        source="seed:market-history",
        symbols=("^NSEI",),
        sectors=("Financials", "Technology"),
    ),
    IngestDocumentRequest(
        title="Dot-Com Bubble: Valuation Excess and the Cost of Concentration",
        content=(
            "Between 1995 and March 2000 the Nasdaq Composite rose roughly five "
            "fold, then fell about 78 percent over the following two and a half "
            "years, taking fifteen years to regain its peak. Many companies that "
            "failed had genuine revenue growth but no path to profitability and "
            "were valued on metrics such as page views rather than cash flow. "
            "The broader market fell far less than the technology sector, so "
            "investors diversified across sectors experienced a materially "
            "smaller drawdown. The episode is the standard reference for two "
            "risks: paying an unjustifiable multiple for growth, and allowing a "
            "single theme to dominate portfolio weight. A correct thesis about a "
            "technology can still produce a permanent loss if the entry price "
            "already discounts it."
        ),
        document_type="research_report",
        source="seed:market-history",
        sectors=("Technology",),
    ),
    IngestDocumentRequest(
        title="Earnings Surprises and Post-Announcement Drift",
        content=(
            "Prices react to earnings relative to expectations, not to the "
            "absolute result: a company can grow profit and still fall if the "
            "market expected more. Research on post-earnings-announcement drift "
            "documents that prices continue moving in the direction of a "
            "surprise for weeks after the release, which is one of the most "
            "persistent documented anomalies in equity markets. Forward guidance "
            "usually moves prices more than the reported quarter, because "
            "guidance revises the whole future path of expectations. A guidance "
            "cut is therefore treated as a fundamental deterioration rather than "
            "a temporary dislocation, and is not comparable to a price fall "
            "caused by an external macro shock."
        ),
        document_type="research_report",
        source="seed:principles",
    ),
    IngestDocumentRequest(
        title="Geopolitical Conflict and the Historical Equity Response",
        content=(
            "Studies of equity behaviour around wars, terrorist attacks and "
            "border conflicts find a recurring shape: a sharp initial fall on "
            "the announcement, elevated volatility for several weeks, and "
            "recovery within months unless the conflict disrupts a critical "
            "commodity supply or triggers a recession. Defence contractors and "
            "energy producers generally outperform; airlines, tourism and "
            "consumer discretionary underperform. Safe havens — gold, the US "
            "dollar, government bonds — attract flows. The practical implication "
            "is that a geopolitical drawdown in a fundamentally sound company is "
            "usually a temporary dislocation, while the corresponding rally in "
            "beneficiary sectors is usually temporary too and fades when the "
            "conflict de-escalates."
        ),
        document_type="research_report",
        source="seed:market-history",
        sectors=("Defense", "Energy"),
    ),
    # --- Investing principles ----------------------------------------------
    IngestDocumentRequest(
        title="The Mathematics of Drawdown Recovery",
        content=(
            "Losses and gains are not symmetric. A 20 percent loss requires a 25 "
            "percent gain to break even, a 50 percent loss requires 100 percent, "
            "and an 80 percent loss requires 400 percent. This asymmetry is why "
            "limiting the depth of drawdowns matters more to long-run compounding "
            "than capturing every upside move. Maximum drawdown is therefore "
            "reported alongside return: two strategies with identical annualized "
            "returns are not equivalent if one reached that return through a 60 "
            "percent decline. It also explains why leverage that survives most "
            "conditions can still be ruinous — a single large drawdown can remove "
            "the capital base needed to participate in the recovery."
        ),
        document_type="research_report",
        source="seed:principles",
    ),
    IngestDocumentRequest(
        title="Diversification, Correlation and Its Limits",
        content=(
            "Portfolio variance depends on the covariance between holdings, not "
            "only on their individual volatilities, so combining assets that do "
            "not move together lowers risk without necessarily lowering expected "
            "return. Most of the available diversification benefit is captured "
            "within roughly 20 to 30 well-chosen positions; beyond that, the "
            "marginal reduction in idiosyncratic risk is small. The critical "
            "limitation is that correlations rise toward one during systemic "
            "crises — precisely when diversification is most needed. Holding "
            "many stocks within a single sector or a single macro factor "
            "provides far less protection than the position count suggests, "
            "which is why concentration should be measured by underlying risk "
            "exposure rather than by number of holdings."
        ),
        document_type="research_report",
        source="seed:principles",
    ),
    IngestDocumentRequest(
        title="Mean Reversion Versus Momentum: When Each Applies",
        content=(
            "Momentum and mean reversion operate on different horizons. Over "
            "three to twelve months, relative strength tends to persist, which "
            "is the basis of momentum strategies. Over three to five years, "
            "extreme relative performance tends to reverse, which is the basis "
            "of value and contrarian strategies. Short-horizon reversals also "
            "appear over days to weeks after sharp moves. The decisive question "
            "for a falling price is whether the cause is transient or "
            "fundamental: a quality company hit by an external macro shock is a "
            "reasonable mean-reversion candidate, while a company whose earnings "
            "power has permanently deteriorated is a value trap in which the "
            "price is falling for a reason that will not reverse."
        ),
        document_type="research_report",
        source="seed:principles",
    ),
    IngestDocumentRequest(
        title="Position Sizing and Risk Budgeting",
        content=(
            "Position size determines how much a given view can affect the "
            "portfolio, so sizing is a risk decision rather than a conviction "
            "statement. Risk-based sizing scales positions by volatility so each "
            "holding contributes comparable risk, which prevents a single "
            "volatile name from dominating outcomes. Risk contribution, not "
            "capital weight, is the right measure: a 10 percent weight in an "
            "asset twice as volatile as the rest contributes far more than 10 "
            "percent of portfolio risk. Practical constraints usually include a "
            "maximum single-position weight, a maximum sector weight, and a "
            "rebalancing rule, because an unrebalanced portfolio drifts toward "
            "whatever has recently appreciated and therefore toward "
            "concentration in the most extended positions."
        ),
        document_type="research_report",
        source="seed:principles",
    ),
    IngestDocumentRequest(
        title="Modern Portfolio Theory and the Efficient Frontier",
        content=(
            "Mean-variance optimization selects portfolio weights that minimize "
            "variance for a target expected return, tracing an efficient "
            "frontier of portfolios that cannot be improved on both dimensions "
            "at once. The tangency portfolio maximizes the Sharpe ratio, the "
            "excess return earned per unit of volatility. The method's known "
            "weakness is sensitivity to inputs: expected returns estimated from "
            "historical averages carry large error, and the optimizer amplifies "
            "that error by concentrating weight in whichever asset happens to "
            "show the highest estimated return. Common mitigations are to "
            "constrain weights, to shrink the covariance matrix toward a "
            "structured estimate, or to use minimum-variance and inverse-"
            "volatility portfolios, which need no expected-return estimates and "
            "are usually more stable out of sample."
        ),
        document_type="research_report",
        source="seed:principles",
    ),
    IngestDocumentRequest(
        title="Reading Sharpe, Sortino and Volatility",
        content=(
            "The Sharpe ratio divides return in excess of the risk-free rate by "
            "the standard deviation of returns, measuring reward per unit of "
            "total variability. The Sortino ratio divides by downside deviation "
            "only, on the reasoning that upside variability is not a risk "
            "investors wish to avoid; it is therefore the more informative "
            "measure for strategies with asymmetric return distributions. Both "
            "are computed on periodic returns and annualized, so the sampling "
            "period must be stated for the number to be comparable. Neither "
            "captures tail risk well, because standard deviation understates the "
            "likelihood of extreme moves in return series with fat tails, which "
            "is why maximum drawdown is normally reported alongside them."
        ),
        document_type="research_report",
        source="seed:principles",
    ),
    IngestDocumentRequest(
        title="Rupee Cost Averaging and Systematic Investment Plans",
        content=(
            "A systematic investment plan contributes a fixed amount at regular "
            "intervals regardless of price, which buys more units when prices "
            "are low and fewer when they are high, producing an average cost "
            "below the average price paid. Its main benefit is behavioural: it "
            "removes the timing decision and keeps contributions running through "
            "drawdowns, which is when accumulation is most valuable. It does not "
            "protect against loss in a sustained decline, and in a steadily "
            "rising market a lump sum invested earlier generally outperforms, "
            "since more capital is exposed for longer. Returns on an irregular "
            "contribution schedule should be measured with a money-weighted "
            "method such as XIRR, because a simple return calculation "
            "misattributes the effect of the timing of cash flows."
        ),
        document_type="research_report",
        source="seed:principles",
    ),
    IngestDocumentRequest(
        title="Distinguishing Transient Shocks From Fundamental Deterioration",
        content=(
            "The practical question after any sharp price fall is whether the "
            "cause changes the company's long-run earning power. Transient and "
            "external causes — geopolitical conflict, a policy or rate decision, "
            "a commodity move, a broad risk-off episode — usually leave the "
            "business intact and historically mean-revert, so weakness in a "
            "financially sound company is a candidate for accumulation. "
            "Fundamental causes — an earnings miss driven by lost share, a "
            "guidance cut, an accounting or governance failure, adverse "
            "regulation that permanently compresses margins, or the loss of a "
            "major customer — change the cash flows themselves and are not "
            "resolved by waiting. The same percentage decline therefore warrants "
            "opposite actions depending on which category the cause falls into."
        ),
        document_type="research_report",
        source="seed:principles",
    ),
    IngestDocumentRequest(
        title="Base Rates and the Limits of Forecasting",
        content=(
            "Short-horizon price forecasts are weak: daily direction models "
            "rarely exceed accuracy in the low fifties percent, and small "
            "differences in sample or period move that figure materially. "
            "Forecast quality generally improves with horizon, because "
            "fundamentals dominate noise over longer periods. Practical "
            "consequences are to weight a forecast by its demonstrated skill "
            "rather than by its stated confidence, to combine several weak but "
            "uncorrelated signals rather than to rely on one, and to state "
            "predictions as probabilities with explicit horizons. A model "
            "reporting a 55 percent probability of an upward move is making a "
            "modest, honest claim; a model reporting 95 percent on daily equity "
            "direction is almost certainly overfitted to its training window."
        ),
        document_type="research_report",
        source="seed:principles",
    ),
    IngestDocumentRequest(
        title="Sector Rotation Across the Business Cycle",
        content=(
            "Sector leadership rotates with the business cycle in a broadly "
            "repeatable order. Early recovery, with falling rates and improving "
            "growth, tends to favour financials, consumer discretionary and "
            "industrials. Mid-cycle expansion favours technology and "
            "industrials. Late cycle, with rising inflation and tightening "
            "policy, favours energy and materials. Contraction favours defensive "
            "sectors — consumer staples, healthcare and utilities — whose demand "
            "is relatively insensitive to income. The rotation is a tendency "
            "rather than a rule, and cycle turning points are only clearly "
            "identifiable after the fact, so it is more useful for interpreting "
            "why a sector is moving than for timing entry into it."
        ),
        document_type="research_report",
        source="seed:principles",
    ),
)


# Purpose:
# The default knowledge base contents for RAG retrieval. Data only — ingestion
# (chunking, embedding, storage) belongs to ResearchService.
