# Universal Scraper - Visual Architecture

## System Flow Diagram

```mermaid
graph TD
    Start[Input: 40 Base URLs + Date Range] --> Engine[Scraper Engine]
    
    Engine --> Sequential[Sequential Processing<br/>2 req/sec rate limit]
    Sequential --> Site1[Site 1]
    Sequential --> Site2[Site 2]
    Sequential --> SiteN[Site N...]
    
    Site1 --> Fetch[Intelligent Page Fetch]
    
    Fetch --> JSCheck{JS Heavy?}
    JSCheck -->|Yes| WaitJS[Wait for Content<br/>networkidle]
    JSCheck -->|No| HTMLReady[HTML Ready]
    WaitJS --> HTMLReady
    
    HTMLReady --> Detect[Page Structure Detection]
    
    Detect --> Score{Check All Patterns}
    Score --> CheckTable[Has Tables?]
    Score --> CheckCal[Has Calendar?]
    Score --> CheckList[Has Lists?]
    Score --> CheckPara[Has Paragraphs?]
    
    CheckTable --> Collect[Collect All Types]
    CheckCal --> Collect
    CheckList --> Collect
    CheckPara --> Collect
    
    Collect --> ExtractAll[Extract from ALL<br/>Detected Types]
    
    ExtractAll -->|If table| TableEx[Table Extractor<br/>Parse rows & columns]
    ExtractAll -->|If calendar| CalEx[Calendar Extractor<br/>Year/Month hierarchy]
    ExtractAll -->|If list| ListEx[List Extractor<br/>Parse list items]
    ExtractAll -->|If paragraph| ParaEx[Paragraph Extractor<br/>Split by dates]
    
    TableEx --> Meetings[Raw Meetings]
    CalEx --> Meetings
    ListEx --> Meetings
    ParaEx --> Meetings
    
    Meetings --> Nav[Adaptive Navigation]
    
    Nav --> Paginate{Pagination?}
    Paginate -->|Yes| NextPage[Navigate Next Page]
    NextPage --> Nav
    Paginate -->|No| YearNav{Year Filters?}
    
    YearNav -->|Yes| ClickYear[Click Year Buttons]
    ClickYear --> Nav
    YearNav -->|No| DetailNav{Detail Pages?}
    
    DetailNav -->|Yes| DetailPage[Navigate to Detail]
    DetailPage --> Nav
    DetailNav -->|No| Classify[Link Classification]
    
    Classify --> Score2[ML-Style Scoring]
    Score2 --> Agenda[Identify Agenda Links]
    Score2 --> Minutes[Identify Minutes Links]
    Score2 --> Video[Identify Video Links]
    
    Agenda --> Validate[Strict Validation]
    Minutes --> Validate
    Video --> Validate
    
    Validate --> Check1{Date Valid?}
    Check1 -->|No| Reject[Reject Meeting]
    Check1 -->|Yes| Check2{In Range?}
    Check2 -->|No| Reject
    Check2 -->|Yes| Check3{Has Links?}
    Check3 -->|No| Reject
    Check3 -->|Yes| Accept[Accept Meeting]
    
    Accept --> Dedup[Deduplication<br/>by date + title]
    Reject --> NextSite[Next Site]
    
    Dedup --> Save[Incremental Save]
    Save --> NextSite
    
    NextSite --> Complete{All Sites Done?}
    Complete -->|No| Sequential
    Complete -->|Yes| Output[JSON Output<br/>Zero False Positives]
    
    style Engine fill:#4CAF50,color:#fff
    style Detect fill:#2196F3,color:#fff
    style Validate fill:#FF5722,color:#fff
    style Output fill:#4CAF50,color:#fff
```

## Extraction Strategy Decision Tree

```mermaid
graph TD
    Page[Webpage HTML] --> Analyze[Analyze ALL Patterns]
    
    Analyze --> CheckAll{Check All Patterns}
    
    CheckAll --> CheckTables[Check Tables<br/>with >3 rows]
    CheckAll --> CheckCalendar[Check Year/Month<br/>Hierarchies]
    CheckAll --> CheckLists[Check Lists<br/>with dates]
    CheckAll --> CheckParagraphs[Check Dense<br/>Paragraphs]
    
    CheckTables --> CollectTypes[Collect Detected Types]
    CheckCalendar --> CollectTypes
    CheckLists --> CollectTypes
    CheckParagraphs --> CollectTypes
    
    CollectTypes --> ExtractAll[Extract from ALL Types]
    
    ExtractAll --> TableEx{Table?}
    ExtractAll --> CalEx{Calendar?}
    ExtractAll --> ListEx{List?}
    ExtractAll --> ParaEx{Paragraph?}
    
    TableEx -->|Yes| TableExtract[Table Extraction]
    CalEx -->|Yes| CalExtract[Calendar Extraction]
    ListEx -->|Yes| ListExtract[List Extraction]
    ParaEx -->|Yes| ParaExtract[Paragraph Extraction]
    
    TableExtract --> Combine[Combine All Results]
    CalExtract --> Combine
    ListExtract --> Combine
    ParaExtract --> Combine
    
    Combine --> Deduplicate[Deduplicate Meetings]
    
    style Analyze fill:#2196F3,color:#fff
    style CollectTypes fill:#FF9800,color:#fff
    style Combine fill:#4CAF50,color:#fff
    style Deduplicate fill:#4CAF50,color:#fff
```

## Error Handling & Retry Logic

```mermaid
graph TD
    Request[HTTP/Browser Request] --> Try[Attempt Fetch]
    
    Try --> Success{Success?}
    Success -->|Yes| Return[Return HTML]
    Success -->|No| ErrorType{Classify Error}
    
    ErrorType -->|Timeout| Backoff[Exponential Backoff<br/>2s → 4s → 8s]
    ErrorType -->|Bot Detection| Fingerprint[Rotate Browser<br/>Fingerprint]
    ErrorType -->|Network Error| Retry[Simple Retry]
    ErrorType -->|Other| Fail[Fail Fast]
    
    Backoff --> RetryCheck{Retries Left?}
    Fingerprint --> RetryCheck
    Retry --> RetryCheck
    
    RetryCheck -->|Yes| Try
    RetryCheck -->|No| LogError[Log Error]
    
    LogError --> NextSite[Move to Next Site]
    
    style Success fill:#4CAF50,color:#fff
    style Backoff fill:#FF9800,color:#fff
    style Fingerprint fill:#2196F3,color:#fff
    style Fail fill:#F44336,color:#fff
```

## Link Classification Algorithm

```mermaid
graph LR
    Link[Found Link] --> Score[Calculate Score]
    
    Score --> KeywordScore[Keyword Score<br/>agenda, minutes, video]
    Score --> DomainScore[Domain Score<br/>youtube, granicus]
    Score --> PositionScore[Position Score<br/>proximity to date]
    Score --> ExtensionScore[Extension Score<br/>.pdf, .mp4]
    
    KeywordScore --> Total[Total Score]
    DomainScore --> Total
    PositionScore --> Total
    ExtensionScore --> Total
    
    Total --> Compare{Compare All Links}
    
    Compare --> Agenda[Highest Agenda Score<br/>→ Agenda URL]
    Compare --> Minutes[Highest Minutes Score<br/>→ Minutes URL]
    Compare --> Video[Highest Video Score<br/>→ Video URL]
    
    style Agenda fill:#4CAF50,color:#fff
    style Minutes fill:#2196F3,color:#fff
    style Video fill:#FF5722,color:#fff
```

## Validation Pipeline

```mermaid
graph TD
    Meeting[Extracted Meeting] --> V1{Date Format<br/>YYYY-MM-DD?}
    V1 -->|No| Reject[❌ REJECT]
    V1 -->|Yes| V2{Date in Range?}
    
    V2 -->|No| Reject
    V2 -->|Yes| V3{Title Non-Empty?}
    
    V3 -->|No| Reject
    V3 -->|Yes| V4{Has at least<br/>1 valid link?}
    
    V4 -->|No| Reject
    V4 -->|Yes| V5{URLs Valid?<br/>No #, mailto:}
    
    V5 -->|No| Reject
    V5 -->|Yes| Dedup[Smart Deduplication]
    
    Dedup --> D1{Same date<br/>+ title?}
    D1 -->|No| Accept[✅ ACCEPT]
    D1 -->|Yes| D2{URLs<br/>overlap?}
    
    D2 -->|Yes| Merge[Merge URLs]
    D2 -->|No| D3{One has<br/>no URLs?}
    
    D3 -->|Yes| Merge
    D3 -->|No| KeepBoth[Keep Separate<br/>Different meetings]
    
    Merge --> Accept
    KeepBoth --> Accept
    
    style Reject fill:#F44336,color:#fff
    style Accept fill:#4CAF50,color:#fff
    style Merge fill:#2196F3,color:#fff
    style KeepBoth fill:#FF9800,color:#fff
```

## Key Components Interaction

```mermaid
graph TD
    CLI[CLI scraper.py] --> Engine[ScraperEngine]
    
    Engine --> Browser[BrowserManager<br/>Stealth Mode]
    Engine --> Extractor[MeetingExtractor]
    Engine --> Resolver[URLResolver]
    
    Browser --> Playwright[Playwright<br/>Anti-Detection]
    
    Extractor --> SiteSpecific[Site-Specific<br/>Handlers]
    Extractor --> Universal[Universal<br/>Extractors]
    
    Universal --> Table[Table Extractor]
    Universal --> Calendar[Calendar Extractor]
    Universal --> Container[Container Detector]
    Universal --> Paragraph[Paragraph Extractor]
    
    Resolver --> YTDlp[yt-dlp Verification]
    Resolver --> HTTP[HTTP HEAD Verification]
    Resolver --> PlatformEx[Platform Extractors<br/>Granicus, Swagit, etc.]
    
    Engine --> Output[JSON Output<br/>Incremental Save]
    
    style Engine fill:#4CAF50,color:#fff
    style Browser fill:#2196F3,color:#fff
    style Universal fill:#FF9800,color:#fff
    style Output fill:#4CAF50,color:#fff
```



## Summary

This architecture demonstrates:

✅ **Intelligent Design**: Multiple strategies, not one-size-fits-all  
✅ **Production-Ready**: Retry logic, validation, error handling  
✅ **Zero False Positives**: Strict validation at every step  
✅ **Smart Deduplication**: Preserves different meetings, merges partial data  
✅ **Scalable**: Sequential processing + rate limiting  
✅ **Observable**: Clear component separation and logging

