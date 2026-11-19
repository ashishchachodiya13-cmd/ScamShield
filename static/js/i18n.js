const I18N = {
  en: {
    appTitle: "ScamShield",
    appSubtitle: "AI-Assisted Scam Decision Support for Senior Citizens",
    disclaimerBadge: "Decision-Support Tool",
    disclaimerText: "This tool assists you in identifying suspicious messages. It is NOT a replacement for the National Cyber Helpline (1930) or Sanchar Saathi / Chakshu.",
    langLabel: "भाषा / Language:",
    
    // Input Screen
    inputHeading: "Check a Suspicious Message or Call",
    inputSubheading: "Paste any message (SMS, WhatsApp, or Call transcript) or upload a photo of the message below.",
    messagePlaceholder: "Paste the suspicious message or call transcript here...\n\nExample: 'Main CBI officer bol raha hu. Aapke naam par arrest warrant hai. Turant 50,000 transfer kijiye aur kisi ko mat batana.'",
    uploadBtn: "📁 Upload Screenshot",
    uploadHelp: "PNG or JPG screenshot from WhatsApp, SMS, or Call Log",
    clearBtn: "Clear",
    analyzeBtn: "🔍 Analyze Message",
    analyzingText: "Analyzing message for red flags...",
    emptyError: "Please enter some message text or upload a screenshot first.",
    
    // OCR Review
    ocrHeading: "Review Text from Screenshot",
    ocrInstruction: "Please compare the extracted text below with your screenshot. Correct any misspelled words or numbers before analyzing.",
    ocrConfirmBtn: "Looks Correct – Analyze Now",
    ocrCancelBtn: "Remove Image",
    ocrProcessing: "Reading text from image...",
    ocrEmpty: "No text was detected in this image. Please upload a clearer photo or type the message directly.",
    
    // Results Screen
    resultHeading: "Analysis Result",
    riskLabel: "Risk Level",
    riskHighTitle: "HIGH RISK – Warning: Likely Scam",
    riskMedTitle: "MEDIUM RISK – Suspicious Communication",
    riskLowTitle: "LOW RISK – Stay Cautious",
    riskZeroTitle: "NO KNOWN RED FLAGS FOUND – Stay Cautious",
    riskZeroSub: "We did not find any known scam patterns, but never consider any unknown message completely 'Safe'. Banks and government agencies will never ask for your passwords or OTPs.",
    categoryLabel: "Detected Scam Type",
    scoreLabel: "Suspicion Score",
    
    // Explanation
    explanationHeading: "Why This Looks Suspicious (Simple Explanation)",
    sourceLlm: "✨ AI Explanation",
    sourceTemplate: "📋 Standard Safety Guide",
    
    // Red flags
    flagsHeading: "Red Flags Detected in this Message",
    noFlagsFound: "No specific manipulation tactics identified.",
    matchedSnippets: "Words detected:",
    
    // Actions
    actionsHeading: "What You Should Do Now",
    dosTitle: "✅ What TO Do",
    dontsTitle: "❌ What NOT To Do",
    helplinesTitle: "🚨 Official Emergency Contacts",
    
    // Feedback
    feedbackHeading: "Was this helpful?",
    feedbackSubheading: "Your anonymous feedback helps us protect more senior citizens. No message content is ever stored.",
    feedbackHelpfulBtn: "👍 Yes, it helped me",
    feedbackUnhelpfulBtn: "👎 Not helpful",
    feedbackCommentPlaceholder: "Optional: Tell us what could be clearer...",
    feedbackSubmitBtn: "Submit Feedback",
    feedbackThanks: "Thank you! Your feedback has been recorded safely.",
    
    // Reset
    checkAnotherBtn: "🔄 Check Another Message",
  },
  
  hi: {
    appTitle: "स्कैमशील्ड (ScamShield)",
    appSubtitle: "वरिष्ठ नागरिकों के लिए संदिग्ध संदेश पहचान व सुरक्षा सहायक",
    disclaimerBadge: "निर्णय सहायता साधन",
    disclaimerText: "यह साधन आपको संदिग्ध संदेशों को समझने में मदद करता है। यह राष्ट्रीय साइबर हेल्पलाइन (1930) या संचार साथी / चक्षु का विकल्प नहीं है।",
    langLabel: "Language / भाषा:",
    
    // Input Screen
    inputHeading: "संदिग्ध संदेश या कॉल की जांच करें",
    inputSubheading: "संदिग्ध एसएमएस, व्हाट्सएप संदेश या फोन कॉल की बातचीत यहाँ पेस्ट करें, या उसका स्क्रीनशॉट अपलोड करें।",
    messagePlaceholder: "संदिग्ध संदेश यहाँ पेस्ट करें...\n\nउदाहरण: 'सीबीआई अधिकारी बोल रहा हूं। तुरंत पैसे ट्रांसफर करें और किसी को मत बताना।'",
    uploadBtn: "📁 स्क्रीनशॉट अपलोड करें",
    uploadHelp: "व्हाट्सएप, एसएमएस या कॉल स्क्रीनशॉट (PNG या JPG)",
    clearBtn: "साफ करें",
    analyzeBtn: "🔍 संदेश की जांच करें",
    analyzingText: "संदेश की जांच की जा रही है...",
    emptyError: "कृपया पहले कोई संदेश लिखें या स्क्रीनशॉट अपलोड करें।",
    
    // OCR Review
    ocrHeading: "स्क्रीनशॉट से पढ़े गए शब्दों की जांच करें",
    ocrInstruction: "कृपया नीचे लिखे शब्दों को अपने स्क्रीनशॉट से मिलाएं। यदि कोई शब्द गलत पढ़ा गया हो तो उसे ठीक करके जांचें।",
    ocrConfirmBtn: "शब्द सही हैं – अब जांच करें",
    ocrCancelBtn: "फोटो हटाएं",
    ocrProcessing: "स्क्रीनशॉट से अक्षर पढ़े जा रहे हैं...",
    ocrEmpty: "इस फोटो में कोई अक्षर नहीं पढ़े जा सके। कृपया अधिक साफ फोटो अपलोड करें या सीधे संदेश लिखें।",
    
    // Results Screen
    resultHeading: "जांच का परिणाम",
    riskLabel: "जोखिम स्तर",
    riskHighTitle: "अत्यधिक जोखिम – चेतावनी: संभावित धोखाधड़ी",
    riskMedTitle: "मध्यम जोखिम – संदिग्ध संदेश",
    riskLowTitle: "कम जोखिम – सतर्क रहें",
    riskZeroTitle: "कोई ज्ञात संदिग्ध संकेत नहीं मिला – सतर्क रहें",
    riskZeroSub: "इस संदेश में कोई जाना-पहचाना ठगी का तरीका नहीं दिखा, लेकिन किसी भी अज्ञात संदेश को पूरी तरह 'सुरक्षित' न मानें। असली बैंक या पुलिस कभी पासवर्ड या ओटीपी नहीं मांगते।",
    categoryLabel: "धोखाधड़ी का प्रकार",
    scoreLabel: "संदेह स्कोर",
    
    // Explanation
    explanationHeading: "यह संदेश संदिग्ध क्यों है? (सरल शब्दों में)",
    sourceLlm: "✨ एआई व्याख्या",
    sourceTemplate: "📋 प्रमाणित सुरक्षा विवरण",
    
    // Red flags
    flagsHeading: "इस संदेश में मिले धोखे के संकेत (Red Flags)",
    noFlagsFound: "कोई विशिष्ट चालाकी नहीं पाई गई।",
    matchedSnippets: "संदेश में मिले शब्द:",
    
    // Actions
    actionsHeading: "अब आपको क्या करना चाहिए?",
    dosTitle: "✅ क्या करें (सुरक्षित कदम)",
    dontsTitle: "❌ क्या कभी न करें",
    helplinesTitle: "🚨 आधिकारिक सहायता केंद्र",
    
    // Feedback
    feedbackHeading: "क्या यह जानकारी आपके काम आई?",
    feedbackSubheading: "आपकी राय अन्य बुजुर्गों को साइबर ठगी से बचाने में मदद करती है। आपका कोई भी संदेश कभी स्टोर नहीं किया जाता।",
    feedbackHelpfulBtn: "👍 हाँ, बहुत मददगार था",
    feedbackUnhelpfulBtn: "👎 मददगार नहीं था",
    feedbackCommentPlaceholder: "वैकल्पिक: हमें बताएं कि क्या और सरल बनाया जा सकता है...",
    feedbackSubmitBtn: "राय भेजें",
    feedbackThanks: "धन्यवाद! आपकी बहुमूल्य राय सुरक्षित रूप से दर्ज कर ली गई है।",
    
    // Reset
    checkAnotherBtn: "🔄 दूसरा संदेश जांचें",
  }
};
