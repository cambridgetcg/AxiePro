# AxiePro Beta Onboarding Guide

**Welcome, beta tester!** 🎉

You're one of the first 10 traders to test AxiePro before launch. This guide will get you up to speed in ~30 minutes.

---

## What is AxiePro?

**The Problem We Solve:**
- Axie floor prices don't tell the full story (a pure Beast ≠ a 0/6 Beast)
- Hard to know if a listing is actually a good deal or just cheap
- Miss opportunities because you can't watch the market 24/7

**Our Solution:**
- **Smart Valuations**: Hedonic pricing model (like real estate) values each Axie based on class, breed count, purity, parts, and recent sales
- **Deal Detection**: Flags listings priced below fair market value (updated every 5 min)
- **Market Analytics**: Track class trends, floor prices, and emerging meta shifts

**Your Role as Beta Tester:**
- Test the platform like you would use it for real trading
- Give honest feedback (weekly 15-min survey)
- Report bugs or confusion
- Help us understand what traders actually need

---

## Quick Start (First 30 Minutes)

### Step 1: Explore the Platform (10 min)

**Homepage** (`/`)
- Overview of AxiePro features
- Quick links to main sections

**Explorer** (`/explorer`)
- **Current Status**: ✅ Working
- **What to do**:
  1. Search for an Axie ID (try a recent sale from marketplace)
  2. View the valuation breakdown
  3. Check "Deal Analysis" section
  4. Compare our valuation to the listing price

**Market** (`/market`)
- **Current Status**: ✅ Working
- **What to do**:
  1. View floor prices by class
  2. Check market volume trends
  3. Filter by class to see specific data

**Deals** (`/deals`)
- **Current Status**: ✅ Working
- **What to do**:
  1. Browse flagged deals (sorted by discount %)
  2. Toggle between "Deals" (20%+ discount) and "Snipes" (40%+ discount)
  3. Filter by class if interested in specific types
  4. Click on a deal to see full valuation details

**Analytics** (`/analytics`)
- **Current Status**: ✅ Working
- **What to do**:
  1. View 24h/7d/30d market statistics
  2. Check sales activity by class
  3. Track floor price changes over time

**Features Coming Soon** (Don't test these yet):
- Breeding Calculator (`/breeding`) - Will calculate breeding ROI
- Portfolio Tracker (`/portfolio`) - Will track your P&L
- Meta Shifts (`/meta`) - Will alert on emerging trends

---

### Step 2: Test Deal Detection (10 min)

**Goal**: Verify if our deal detector is actually useful.

**How to Test**:

1. **Go to /deals page**

2. **Pick 3 flagged deals**:
   - Note the Axie ID, valuation, listing price, discount %

3. **Check if they're actually good deals**:
   - Go to Sky Mavis marketplace
   - Search for similar Axies (same class, similar purity)
   - Compare prices
   - Ask yourself: "Would I buy this?"

4. **Track outcomes** (optional but helpful):
   - Did the flagged deal sell quickly?
   - Did it sell at the listing price or higher?
   - Was it actually undervalued or just cheap for a reason?

**Give Feedback**:
- In Discord #beta-testing channel, share your findings
- Example: "Checked deal #12345, Beast 6/6, AxiePro said 20% undervalued. Compared to similar listings and agreed—this was a good catch!"

---

### Step 3: Join Beta Discord (5 min)

**Discord Invite**: [INSERT INVITE LINK]

**Channels**:
- **#announcements**: Updates from the team
- **#beta-testing**: General discussion, questions, bug reports
- **#feedback**: Share detailed feedback
- **#deals-chat**: Discuss specific deals you found

**Introduce yourself**:
```
Hey! I'm [name/handle], been trading Axies for [timeframe].
Mainly trade [class] Axies.
Excited to test AxiePro and help shape it!
```

---

### Step 4: First Week Goals (Ongoing)

**Your Mission** (if you choose to accept it):

- [  ] Use Explorer to value 5+ Axies
- [  ] Check /deals page at least once per day
- [  ] Review market analytics weekly
- [  ] Report at least 1 bug or suggestion
- [  ] Complete the weekly feedback survey (sent Fridays)

---

## How to Give Feedback

### Option 1: Weekly Survey (Structured)

**When**: Every Friday at 5pm EST
**Time**: 15 minutes
**Format**: Google Form with 10 questions

**Questions Include**:
1. How many times did you use AxiePro this week?
2. Which features did you use? (checkboxes)
3. Did you find any deals you acted on?
4. How accurate were the valuations compared to your judgment? (1-5 scale)
5. What confused you or felt clunky?
6. What feature would make you use this daily?
7. Would you pay for this? If yes, how much?
8. Anything else to share?

**Action**: Check your email Friday afternoon for survey link.

---

### Option 2: Discord (Anytime Feedback)

**For Quick Feedback**:
Post in #beta-testing:
```
💡 Suggestion: [your idea]
🐛 Bug: [what broke]
❓ Question: [unclear behavior]
🎯 Deal Feedback: [deal #12345 was accurate/inaccurate because...]
```

**For Detailed Feedback**:
Post in #feedback:
```
**Feature**: [which feature]
**What I tried**: [step-by-step]
**What happened**: [result]
**What I expected**: [expected behavior]
**Suggestion**: [how to improve]
```

---

### Option 3: Direct Message (Sensitive Issues)

**For**:
- Bugs with personal data
- Sensitive trading strategies
- Private feature requests

**How**: DM @[Developer Handle] on Discord

---

## Feature Overview (What's Working)

### 1. Explorer (Axie Valuation)

**What it does**:
- Enter an Axie ID → Get fair market valuation
- Shows breakdown by class, breed count, purity, parts
- Compares to recent sales and floor prices

**How our model works** (transparency):
- Hedonic pricing: Every trait has a value weight
- Trained on 30,000+ historical sales
- Updated weekly with new data
- Confidence score: How certain we are

**Accuracy**: Target >70% (we're testing this with your help!)

**Key Fields**:
- **Hedonic Value**: Our calculated fair market price
- **Confidence**: How sure we are (higher = better)
- **Class Floor**: Current floor for this class
- **Deal Score**: 0-100 (higher = better deal)

---

### 2. Market (Floor Prices & Trends)

**What it does**:
- Shows current floor price by class
- Tracks 24h/7d/30d price changes
- Displays market volume

**How to use**:
- Check before buying: Is this class trending up or down?
- Compare listings to floor: Is this below/above floor?

**Data Freshness**: <1 hour (listings updated every 5 min)

---

### 3. Deals (Undervalued Axies)

**What it does**:
- Auto-detects listings below fair market value
- Sorts by discount % (best deals first)
- Updates every 5 minutes

**Two Categories**:
- **Deals** (20-40% discount): Good value, realistic opportunities
- **Snipes** (40%+ discount): Rare, often get bought fast

**How Deal Score Works**:
- 0-50: Weak deal (might be cheap for a reason)
- 50-70: Solid deal (worth investigating)
- 70-85: Great deal (likely accurate)
- 85-100: Amazing deal (snipe territory, verify it's real)

**Filters**:
- **Class**: Focus on your preferred class
- **Min Score**: Adjust threshold (50 = show all deals, 70 = only strong deals)

---

### 4. Analytics (Market Insights)

**What it does**:
- Aggregates sales data by timeframe
- Shows volume trends
- Tracks floor price changes

**Use Cases**:
- Weekly recap: How was the market this week?
- Class comparison: Which class is hottest right now?
- Volume tracking: Is trading activity up or down?

---

## Common Questions (FAQ)

### Q: How often is data updated?
**A**:
- Listings: Every 5 minutes
- Sales: Every 30 minutes
- Floor prices: Every hour
- Valuations: Model retrained weekly

### Q: How accurate are the valuations?
**A**:
- Target: >70% accuracy
- Currently testing with your help!
- If you find inaccurate valuations, please report them with details

### Q: What if I find a deal and it's already sold?
**A**:
- Deals update every 5 min, but Axies can sell instantly
- Best deals go fast—that's normal
- If >50% of flagged deals are already sold, tell us (might need faster updates)

### Q: Can I use this on mobile?
**A**:
- Yes, responsive design
- Some features may be clunky on mobile (tell us which ones!)

### Q: What data do you collect about me?
**A**:
- If you connect wallet: Your wallet address (for portfolio tracking)
- Usage analytics: What features you use, page load times (anonymous)
- No personal data, no email required (yet)

### Q: Will this be free forever?
**A**:
- Free tier will always exist (limited features)
- Premium tier launching in 4-6 weeks
- As a beta tester: **50% off Premium for life**

### Q: What will Premium include?
**A** (not final, might change based on feedback):
- Unlimited valuations (free tier: 3/day)
- Real-time deal alerts (email/Discord webhook)
- Portfolio tracking with P&L
- Breeding ROI calculator
- Meta shift notifications
- CSV export for taxes
- API access

### Q: How do I report a bug?
**A**:
- Discord: Post in #beta-testing with "[BUG]" prefix
- Include: What you did, what happened, what you expected
- Screenshots help!

### Q: Can I invite friends to beta?
**A**:
- Not yet—we want to keep the group small for now
- After 2 weeks, we might expand to 20-30 testers
- Your friends can join the waitlist for public launch

---

## How to Report Bugs

**Good Bug Report** (we can fix this):
```
[BUG] Deal score shows NaN for Axie #12345

Steps to reproduce:
1. Go to /deals
2. Filter for "Beast" class
3. Click on Axie #12345
4. Deal score shows "NaN" instead of a number

Expected: Should show a score between 0-100
Actual: Shows "NaN"
Screenshot: [attached]
Browser: Chrome 119, macOS
```

**Vague Bug Report** (hard to fix):
```
The deals page is broken
```

**Info to Include**:
- What you were trying to do
- Step-by-step to reproduce
- What happened vs. what you expected
- Browser + OS
- Screenshot (if visual bug)

---

## What We're Testing For

### Primary Goals (Help us validate these)

1. **Valuation Accuracy**
   - Do our valuations match your intuition as a trader?
   - When they don't match, why? (Missing a key trait? Market changed?)

2. **Deal Detection Usefulness**
   - Are flagged deals actually good opportunities?
   - Or are they cheap for a reason (bad parts, too many breeds, etc.)?

3. **UX Clarity**
   - Can you figure out how to use features without reading docs?
   - Where did you get confused?

4. **Speed & Performance**
   - Do pages load fast enough? (<2 seconds)
   - Any lag or freezing?

### Secondary Goals (Nice to have feedback)

5. **Feature Priorities**
   - Which features do you use most?
   - Which coming-soon features are you most excited about?

6. **Willingness to Pay**
   - Would you pay for this if it helped you find 1-2 good deals per month?
   - How much? ($5/mo? $10/mo? $20/mo?)

---

## Your Beta Tester Perks

✅ **Early Access**: Use AxiePro before anyone else
✅ **Direct Line to Developer**: Your feedback shapes the product
✅ **Lifetime 50% Discount**: When Premium launches, you pay half-price forever
✅ **Recognition**: Thank you in launch announcement (if you want)
✅ **Insider Knowledge**: See our roadmap, vote on features

---

## Beta Testing Timeline

**Week 1** (This week):
- Onboarding + exploration
- First feedback survey Friday
- Goal: Get comfortable with all features

**Week 2**:
- Active usage + deal testing
- Second feedback survey Friday
- Goal: Validate accuracy of valuations

**Week 3**:
- Feature requests + polish feedback
- Third feedback survey Friday
- Goal: Identify must-have features for launch

**Week 4**:
- Final testing before public launch
- Final feedback survey
- Goal: Zero critical bugs, smooth UX

**Week 5-6**:
- Premium tier soft launch (to beta testers first)
- Pricing validation
- Goal: 5+ beta testers convert to paid

---

## Next Steps

**Right now** (next 30 min):
- [  ] Browse the platform (try all features)
- [  ] Join beta Discord
- [  ] Introduce yourself in #beta-testing

**This week**:
- [  ] Use Explorer to value 5+ Axies
- [  ] Check /deals daily
- [  ] Report 1+ bug or suggestion
- [  ] Complete Friday's survey

**Questions?**
- Ask in Discord #beta-testing
- DM @[Developer Handle]
- Email: [beta@axiepro.io] (if set up)

---

**Thank you for being an early believer!** 🙏

Your feedback will directly shape AxiePro into the tool traders actually want.

Let's build something great together 🚀

---

**Document Version**: 1.0
**Last Updated**: 2026-01-30
**Next Update**: After W1 completes (when all features confirmed working)
