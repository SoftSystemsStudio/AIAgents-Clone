# Google Analytics Setup & Demo Tracking Guide

## Current Status

✅ **Google Analytics Active**: Property ID `G-8KJVEMXLGQ`  
✅ **Demo Event Tracking**: Implemented and active  
✅ **Conversion Tracking**: CTA clicks monitored

## Demo Events Being Tracked

### 1. Demo Tab Switching
**Event Name**: `demo_tab_switch`  
**Triggered**: When user clicks between Email, Data, Booking, or Support tabs  
**Parameters**:
- `agent_type`: email | data | booking | support
- `event_category`: Demo Interaction

### 2. Scenario Selection
**Event Name**: `demo_scenario_select`  
**Triggered**: When user selects a scenario from dropdown  
**Parameters**:
- `agent_type`: email | data | booking | support
- `scenario`: inquiry | complaint | linkedin | extract | clean | validate | pricing | order | technical | refund
- `event_category`: Demo Interaction

### 3. Demo Completion
**Event Name**: `demo_completed`  
**Triggered**: When demo finishes processing and shows output  
**Parameters**:
- `agent_type`: email | data | booking | support
- `scenario`: (scenario name)
- `event_category`: Demo Completion

### 4. Demo Milestones
**Event Name**: `demo_milestone`  
**Triggered**: Every 100 demos (counter hits 2900, 3000, 3100, etc.)  
**Parameters**:
- `milestone`: 100 | 200 | 300 | ...
- `event_category`: Demo Engagement

### 5. Demo to Consultation
**Event Name**: `demo_to_consultation`  
**Triggered**: When user clicks "Book a Free Consultation" CTA  
**Parameters**:
- `event_category`: Conversion
- `event_label`: Demo Section CTA

## Google Analytics 4 Dashboard Setup

### Quick Access Queries

**Most Popular Agent**:
```
GA4: Reports → Engagement → Events → demo_tab_switch
Group by: agent_type
Metric: Event count
```

**Completion Rate**:
```
Calculate: (demo_completed count / demo_tab_switch count) × 100
Target: >60%
```

**Conversion Rate**:
```
Calculate: (demo_to_consultation / demo_completed) × 100
Target: >10%
```

### Creating Custom Exploration

1. Go to **Explore** section in GA4
2. Create **Funnel Exploration**
3. Add steps:
   - Step 1: `page_view` (landing page)
   - Step 2: `demo_tab_switch` (engaged)
   - Step 3: `demo_completed` (completed)
   - Step 4: `demo_to_consultation` (converted)
   - Step 5: `form_submit` (booked)

## Key Metrics to Monitor

| Metric | How to Calculate | Target |
|--------|------------------|--------|
| **Demo Engagement Rate** | Users who clicked demo / Total visitors | >40% |
| **Demo Completion Rate** | demo_completed / demo_tab_switch | >60% |
| **Demos per User** | demo_completed / Unique users | >2.0 |
| **Conversion Rate** | demo_to_consultation / demo_completed | >10% |
| **Top Agent** | Most clicked demo_tab_switch | Track trend |

## Weekly Analytics Checklist

- [ ] Review total demos completed (compare to last week)
- [ ] Check which agent is most popular
- [ ] Calculate completion rate (should be >60%)
- [ ] Calculate conversion rate (should be >10%)
- [ ] Review top scenarios per agent
- [ ] Check average demos per user
- [ ] Identify drop-off points
- [ ] Test all demo buttons working

## Setup Instructions for New GA4 Properties

### Step 1: Create Google Analytics Account

Replace `G-XXXXXXXXXX` in `index.html` with your actual Measurement ID:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-YOUR-ID-HERE"></script>
<script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-YOUR-ID-HERE');
</script>
```

**Location**: Lines 7-14 in `index.html` (right after the title tag)

## Step 3: Add to Vercel Environment Variables (Optional)

For better security, you can load the GA ID from environment variables:

1. In Vercel dashboard → Settings → Environment Variables
2. Add new variable:
   - Key: `GOOGLE_ANALYTICS_ID`
   - Value: `G-YOUR-ID-HERE`
3. Update `build.sh` to generate it:
   ```bash
   GOOGLE_ANALYTICS_ID: '${GOOGLE_ANALYTICS_ID:-G-XXXXXXXXXX}'
   ```

## Step 4: Deploy Changes

```bash
git add index.html
git commit -m "feat: Add Google Analytics tracking"
git push
```

Vercel will automatically redeploy (takes ~1-2 minutes).

## Step 5: Verify Tracking is Working

### Real-time Test:
1. Go to Google Analytics → Reports → Realtime
2. Open your site: https://ai-agents-ruddy.vercel.app
3. You should see yourself as an active user!

### Wait 24-48 hours for full reports to populate

## What We're Tracking

### Automatic Events (Google Analytics 4):
- ✅ **Page views** - Every time someone visits
- ✅ **Session start** - New visitor session
- ✅ **First visit** - First time user
- ✅ **Scroll depth** - How far down the page
- ✅ **Outbound clicks** - Links to external sites
- ✅ **File downloads** - If you add PDFs/files

### Custom Events We Added:
- ✅ **form_submission** - When contact form succeeds
  - Category: Contact
  - Label: Contact Form
  - Service: Which service they're interested in
  - Value: 1 (for conversion counting)

## Key Metrics to Monitor

### Acquisition:
- **Traffic sources**: Where visitors come from
  - Organic search (Google)
  - Direct (typed URL or bookmark)
  - Referral (other websites)
  - Social (Twitter, LinkedIn, etc.)

### Engagement:
- **Average engagement time**: How long people stay
- **Engaged sessions per user**: Quality of visits
- **Events per session**: Interaction level

### Conversions:
- **Form submissions**: Your most important metric!
- **Conversion rate**: Visitors → Leads %
- **Goal completions**: Track revenue when sales start

## Setting Up Conversions in GA4

1. Go to **Admin** → Property → **Events**
2. Click **Create event** → "Mark as conversion"
3. Check the box next to `form_submission`
4. Now it's tracked as a conversion!

## Recommended Reports to Check Weekly

1. **Realtime** - See current visitors
2. **Acquisition Overview** - Where traffic comes from
3. **Engagement → Pages and screens** - Most viewed pages
4. **Conversions** - Form submission count
5. **User attributes** - Demographics (age, location)

## Advanced: Set Up Goals & Funnels

### Goal: Get 5 form submissions per week

1. In GA4, go to **Admin** → **Custom definitions**
2. Create custom metrics for tracking:
   - Contact Form Starts (when form is focused)
   - Contact Form Completions (successful submission)
   - Conversion Rate = Completions / Page Views

### Funnel Analysis:
1. Page Load
2. Scroll to Contact Section
3. Form Start (click in field)
4. Form Submit
5. Success Message

This shows where people drop off!

## Troubleshooting

### "No data showing in GA4"
- Wait 24-48 hours for initial data
- Check Realtime report (instant)
- Verify Measurement ID is correct
- Check browser console for errors
- Make sure ad blockers are disabled for testing

### "Tracking code not found"
- View page source, search for "gtag"
- Should see Google Analytics script in `<head>`
- Redeploy if missing after push

### "Events not showing"
- Submit the form yourself
- Check Realtime → Events
- Look for `form_submission` event
- May take 5-10 minutes to appear

## Privacy Considerations

Google Analytics 4 is GDPR/CCPA compliant by default:
- ✅ No personally identifiable information (PII) tracked
- ✅ IP addresses anonymized
- ✅ Cookie consent not required for basic analytics (in most regions)

**Optional**: Add cookie consent banner if you want to be extra cautious:
- Use tools like CookieYes, Osano, or Termly
- Free tiers available

## Next Steps After Setup

1. **Share access** with team members:
   - Admin → Property Access Management
   - Add emails with Viewer or Editor role

2. **Set up email reports**:
   - Get weekly/monthly summaries delivered

3. **Connect to Google Search Console**:
   - See what keywords bring traffic
   - Find SEO opportunities

4. **Install GA4 Chrome extension**:
   - Quick access to reports
   - Realtime notifications

## Expected Results (First Week)

Based on typical landing page performance:

- **Traffic**: 0-50 visitors (organically, no ads yet)
- **Bounce rate**: 40-70% (normal for landing pages)
- **Form submissions**: 0-2 (conversion rate ~2-5%)
- **Avg. time on page**: 1-3 minutes

**To increase traffic:**
- Share on social media
- Post in relevant communities
- Start Google Ads campaign
- SEO optimization (titles, meta descriptions)

## Questions?

Check Google Analytics help: https://support.google.com/analytics/

---

**Status**: ✅ Tracking code added to `index.html`  
**Next**: Get your Measurement ID and replace `G-XXXXXXXXXX`
