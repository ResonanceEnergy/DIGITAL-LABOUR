# Inner Council Intelligence System - Setup Guide

## 🎯 **Inner Council Overview**

The Inner Council Intelligence System monitors **52 council members** (47 human intelligence sources + 5 AI emulation agents) as your daily intelligence source for policy adjustments, steering, planning, and execution. This system serves as your "beginning sensory input from real world data" for project planning and integration.

## 📋 **Current Council Members (52 Total - Council 52)**

### **Primary Council (28 members - Critical/High Priority)**
### **Intelligence Coordination**
- **J Bravo** (intelligence_coordinator) - Strategic intelligence synthesis

### **Business & Strategy**
- **Tom Bilyeu** (business_strategy) - Impact Theory founder
- **Alex Hormozi** (business_scaling) - Business scaling expert
- **Andrei Jikh** (startup_strategy) - Startup strategy expert
- **Ben Wehrman** (marketing_strategy) - Marketing strategy expert

### **AI & Technology**
- **Lex Fridman** (ai_technology) - AI researcher and podcast host
- **The AI Grid** (ai_development) - AI development insights
- **Stefan Burns** (tech_innovation) - Technology innovation

### **Financial & Economic**
- **Nate B Jones** (financial_intelligence) - Financial analysis
- **FARZAD FM** (market_analyst) - Market analysis
- **Ian Carroll Show** (economic_analyst) - Economic analysis
- **Eurodollar University** (financial_education) - Financial education
- **Principles by Ray Dalio** (economic_principles) - Economic principles
- **Instead of Working** (passive_income) - Passive income strategies

### **Cultural & Personal Development**
- **Joe Rogan** (cultural_intelligence) - Cultural commentary
- **Chris Willx** (personal_development) - Personal development
- **The Diary Of A CEO** (ceo_insights) - CEO insights

### **Science & Consciousness**
- **Brighter with Herbert** (consciousness_explorer) - Consciousness exploration
- **Dan Winter Fractal Field** (physics_consciousness) - Physics and consciousness
- **Thunderbolts Project** (plasma_physics) - Plasma physics research

### **Global Systems & Operations**
- **Restitutor Orbis** (global_systems) - Global systems analysis
- **Nomad Capitalist** (global_citizenship) - Global citizenship
- **Tom Scryleus** (geopolitical_analyst) - Geopolitical analysis
- **Spencer Gatten** (operations_expert) - Operations expertise
- **The Inner Operator** (operations_strategy) - Operations strategy

### **Industry Specific**
- **Stripe** (fintech_innovation) - Fintech innovation
- **Space Weather News** (space_intelligence) - Space weather intelligence
- **Energi Media** (energy_analyst) - Energy analysis

### **Secondary Council (19 members - Secondary Priority)**
### **News & Current Events**
- **CNN** (news_mainstream) - Mainstream news and current events
- **BBC** (news_mainstream) - British Broadcasting Corporation news
- **Reuters** (news_mainstream) - Global news and financial reporting
- **AP News** (news_mainstream) - Associated Press news coverage

### **Financial News**
- **Bloomberg** (financial_news) - Financial news and market analysis
- **CNBC** (financial_news) - Business and financial news
- **Financial Times** (financial_news) - Global financial journalism
- **Wall Street Journal** (financial_news) - Business and financial news

### **Technology News**
- **TechCrunch** (tech_news) - Technology news and startups
- **The Verge** (tech_news) - Technology and consumer electronics
- **Wired** (tech_news) - Technology and culture
- **Ars Technica** (tech_news) - Technology news and analysis

### **Science Education**
- **PBS Space Time** (science_education) - Physics and space science education
- **Vsauce** (science_education) - Science and philosophy education
- **Kurzgesagt** (science_education) - Science and educational animations
- **SciShow** (science_education) - Science education and news

### **Business Insights**
- **Harvard Business Review** (business_insights) - Business research and insights
- **TED** (business_insights) - Ideas worth spreading
- **Inc. Magazine** (business_insights) - Entrepreneurship and business growth

### **Emulation Council (5 Members - Supreme Strategic Authority)**
### **AI Emulation Agents**
- **Elon Musk Emulation Agent** (strategic_visionary) - AI-driven emulation of Elon Musk's strategic vision and innovation approach
- **Jamie Dimon Emulation Agent** (financial_leadership) - AI-driven emulation of Jamie Dimon's banking and financial leadership
- **Warren Buffett Emulation Agent** (value_investing) - AI-driven emulation of Warren Buffett's value investing and business wisdom
- **Ryan Cohen Emulation Agent** (retail_investing) - AI-driven emulation of Ryan Cohen's retail and meme stock strategies
- **Agent AZ - Chairman of Council 52** (council_chairman) - AI-driven chairman overseeing the Council 52 strategic coordination

## 🔑 **YouTube API Setup (Required for Live Data)**

### **Step 1: Get YouTube API Key**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable YouTube Data API v3
4. Create credentials (API Key)
5. Copy the API key

### **Step 2: Set API Key**
Choose one of these methods:

**Option A: Environment Variable (Recommended)**
```bash
# Windows PowerShell
$env:YOUTUBE_API_KEY = "your_api_key_here"

# Windows Command Prompt
set YOUTUBE_API_KEY=your_api_key_here
```

**Option B: Add to Config File**
Edit `inner_council_config.json` and add:
```json
{
  "youtube_api_key": "your_api_key_here",
  ...rest of config
}
```

### **Step 3: Verify Setup**
```bash
python youtube_intelligence_monitor.py
```
Should show: "YouTube API key found" instead of warning.

## 🚀 **Running the Inner Council System**

### **Method 1: Direct Python Execution**
```bash
python youtube_intelligence_monitor.py
```

### **Method 2: Batch File**
```bash
.\youtube_monitor.bat
```

### **Method 3: Main Runner Menu**
```bash
.\run_locally.bat
# Select option for Inner Council Intelligence
```

## 📊 **What the System Does**

### **Daily Intelligence Gathering**
- Monitors latest videos from all **47 council members** (28 primary + 19 secondary)
- Analyzes content for trends, insights, and opportunities
- Generates intelligence directives for policy adjustments
- Creates daily reports with actionable recommendations

### **Priority Levels**
- **Critical**: Immediate action required (primary council core members)
- **High**: Short-term attention needed (primary council specialists)
- **Medium**: Medium-term consideration (primary council generalists)
- **Secondary**: Background monitoring (secondary council - monthly review)
- **Low**: Long-term strategic planning

### **Output Files Generated**
```
inner_council_intelligence/
├── daily_report_YYYYMMDD_HHMMSS.md    # Human-readable report
├── directives_YYYYMMDD_HHMMSS.json    # Intelligence directives
└── inner_council_intelligence.log     # System logs

daily_policy_directives/
└── adjustments_YYYYMMDD_HHMMSS.json   # Policy recommendations
```

### **Intelligence Categories**
- **Policy Adjustments**: Daily operational changes
- **Strategic Steering**: Long-term direction updates
- **Project Planning**: New initiative recommendations
- **Execution Guidance**: Tactical implementation advice

## ⚙️ **Configuration Options**

### **Council Member Priorities**
Each council member has a priority level (1-5):
- **5**: Critical daily intelligence
- **4**: High importance
- **3**: Standard monitoring
- **2**: Occasional insights
- **1**: Background monitoring

### **Monitoring Settings**
- **Videos per Member**: 10 most recent videos
- **Content Analysis**: Titles, descriptions, engagement
- **Update Frequency**: Daily execution (can be automated)

## 🔧 **Troubleshooting**

### **"No YouTube API key found"**
- Set the `YOUTUBE_API_KEY` environment variable
- Or add `"youtube_api_key"` to `inner_council_config.json`

### **Empty Reports**
- API key not working (check quota/limits)
- Network connectivity issues
- YouTube API service outages

### **Channel Not Found Errors**
- Verify channel IDs in `inner_council_config.json`
- Some channels may have changed IDs or been terminated

## 🎯 **Integration with DIGITAL LABOUR**

### **Daily Operations**
- Inner Council intelligence feeds into autonomous agents
- Policy adjustments automatically applied to operations
- Strategic steering influences project direction
- Execution guidance optimizes daily workflows

### **Decision Making**
- Real-world data from thought leaders
- Trend analysis for proactive planning
- Risk assessment and opportunity identification
- Cultural and technological intelligence synthesis

## 📈 **Next Steps**

1. **Set up YouTube API key** for live data monitoring
2. **Run initial intelligence gathering** session
3. **Review generated reports** and policy recommendations
4. **Integrate insights** into your daily operations
5. **Schedule automated daily runs** for continuous intelligence

---

## 🎉 **Ready for Inner Council Intelligence**

Your Inner Council of 28 YouTube thought leaders is configured and ready to provide daily intelligence for policy adjustments, steering, planning, and execution. This system will serve as your primary source of real-world data analysis and decision-making guidance.

**Run the system now:**
```bash
python youtube_intelligence_monitor.py
```

*Watch as your Inner Council analyzes the latest content from J Bravo, Tom Bilyeu, Lex Fridman, Joe Rogan, and 24 other thought leaders to guide your DIGITAL LABOUR operations!* 🚀🧠⚡</content>
<parameter name="filePath">C:\Dev\DIGITAL-LABOUR\INNER_COUNCIL_SETUP_GUIDE.md