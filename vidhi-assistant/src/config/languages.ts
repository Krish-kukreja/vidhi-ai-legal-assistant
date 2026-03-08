// Configuration for 22 Official Indian Languages + Regional Dialects

export interface LanguageConfig {
  code: string; // ISO 639-1 or custom code
  name: string; // English name
  nativeName: string; // Native script name
  script: string; // Writing script
  awsTranscribeSupported: boolean;
  awsPollySupported: boolean;
  awsPollyVoice?: string;
  bhashiniSupported: boolean;
  isDialect: boolean;
  fallbackLanguage?: string; // Fallback if service unavailable
  bcp47: string; // BCP 47 language tag for browser APIs
}

export const INDIAN_LANGUAGES: Record<string, LanguageConfig> = {
  // 1. Hindi (हिन्दी)
  hindi: {
    code: "hi",
    name: "Hindi",
    nativeName: "हिन्दी",
    script: "Devanagari",
    awsTranscribeSupported: true,
    awsPollySupported: true,
    awsPollyVoice: "Kajal", // Neural voice: Kajal (female), Aditi (female)
    bhashiniSupported: true,
    isDialect: false,
    bcp47: "hi-IN",
  },

  // 2. Bengali (বাংলা)
  bengali: {
    code: "bn",
    name: "Bengali",
    nativeName: "বাংলা",
    script: "Bengali",
    awsTranscribeSupported: true,
    awsPollySupported: true,
    awsPollyVoice: "Tanishaa", // Neural voice
    bhashiniSupported: true,
    isDialect: false,
    bcp47: "bn-IN",
  },

  // 3. Telugu (తెలుగు)
  telugu: {
    code: "te",
    name: "Telugu",
    nativeName: "తెలుగు",
    script: "Telugu",
    awsTranscribeSupported: true,
    awsPollySupported: false, // AWS Polly doesn't support Telugu yet
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: false,
    bcp47: "te-IN",
  },

  // 4. Marathi (मराठी)
  marathi: {
    code: "mr",
    name: "Marathi",
    nativeName: "मराठी",
    script: "Devanagari",
    awsTranscribeSupported: true,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: false,
    bcp47: "mr-IN",
  },

  // 5. Tamil (தமிழ்)
  tamil: {
    code: "ta",
    name: "Tamil",
    nativeName: "தமிழ்",
    script: "Tamil",
    awsTranscribeSupported: true,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: false,
    bcp47: "ta-IN",
  },

  // 6. Urdu (اردو)
  urdu: {
    code: "ur",
    name: "Urdu",
    nativeName: "اردو",
    script: "Perso-Arabic",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: false,
    fallbackLanguage: "hindi",
    bcp47: "ur-IN",
  },

  // 7. Gujarati (ગુજરાતી)
  gujarati: {
    code: "gu",
    name: "Gujarati",
    nativeName: "ગુજરાતી",
    script: "Gujarati",
    awsTranscribeSupported: true,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: false,
    bcp47: "gu-IN",
  },

  // 8. Kannada (ಕನ್ನಡ)
  kannada: {
    code: "kn",
    name: "Kannada",
    nativeName: "ಕನ್ನಡ",
    script: "Kannada",
    awsTranscribeSupported: true,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: false,
    bcp47: "kn-IN",
  },

  // 9. Malayalam (മലയാളം)
  malayalam: {
    code: "ml",
    name: "Malayalam",
    nativeName: "മലയാളം",
    script: "Malayalam",
    awsTranscribeSupported: true,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: false,
    bcp47: "ml-IN",
  },

  // 10. Odia (ଓଡ଼ିଆ)
  odia: {
    code: "or",
    name: "Odia",
    nativeName: "ଓଡ଼ିଆ",
    script: "Odia",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: false,
    fallbackLanguage: "hindi",
    bcp47: "or-IN",
  },

  // 11. Punjabi (ਪੰਜਾਬੀ)
  punjabi: {
    code: "pa",
    name: "Punjabi",
    nativeName: "ਪੰਜਾਬੀ",
    script: "Gurmukhi",
    awsTranscribeSupported: true,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: false,
    bcp47: "pa-IN",
  },

  // 12. Assamese (অসমীয়া)
  assamese: {
    code: "as",
    name: "Assamese",
    nativeName: "অসমীয়া",
    script: "Bengali",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: false,
    fallbackLanguage: "bengali",
    bcp47: "as-IN",
  },

  // 13. Maithili (मैथिली)
  maithili: {
    code: "mai",
    name: "Maithili",
    nativeName: "मैथिली",
    script: "Devanagari",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: true,
    fallbackLanguage: "hindi",
    bcp47: "mai-IN",
  },

  // 14. Santali (ᱥᱟᱱᱛᱟᱲᱤ)
  santali: {
    code: "sat",
    name: "Santali",
    nativeName: "ᱥᱟᱱᱛᱟᱲᱤ",
    script: "Ol Chiki",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: false,
    isDialect: false,
    fallbackLanguage: "hindi",
    bcp47: "sat-IN",
  },

  // 15. Kashmiri (कॉशुर / کٲشُر)
  kashmiri: {
    code: "ks",
    name: "Kashmiri",
    nativeName: "कॉशुर",
    script: "Perso-Arabic/Devanagari",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: false,
    isDialect: false,
    fallbackLanguage: "urdu",
    bcp47: "ks-IN",
  },

  // 16. Nepali (नेपाली)
  nepali: {
    code: "ne",
    name: "Nepali",
    nativeName: "नेपाली",
    script: "Devanagari",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: false,
    isDialect: false,
    fallbackLanguage: "hindi",
    bcp47: "ne-IN",
  },

  // 17. Konkani (कोंकणी)
  konkani: {
    code: "kok",
    name: "Konkani",
    nativeName: "कोंकणी",
    script: "Devanagari",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: false,
    fallbackLanguage: "marathi",
    bcp47: "kok-IN",
  },

  // 18. Sindhi (سنڌي / सिन्धी)
  sindhi: {
    code: "sd",
    name: "Sindhi",
    nativeName: "सिन्धी",
    script: "Perso-Arabic/Devanagari",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: false,
    isDialect: false,
    fallbackLanguage: "hindi",
    bcp47: "sd-IN",
  },

  // 19. Dogri (डोगरी)
  dogri: {
    code: "doi",
    name: "Dogri",
    nativeName: "डोगरी",
    script: "Devanagari",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: false,
    isDialect: false,
    fallbackLanguage: "hindi",
    bcp47: "doi-IN",
  },

  // 20. Manipuri (মৈতৈলোন্)
  manipuri: {
    code: "mni",
    name: "Manipuri",
    nativeName: "মৈতৈলোন্",
    script: "Bengali/Meitei Mayek",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: false,
    fallbackLanguage: "bengali",
    bcp47: "mni-IN",
  },

  // 21. Bodo (बड़ो)
  bodo: {
    code: "brx",
    name: "Bodo",
    nativeName: "बड़ो",
    script: "Devanagari",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: false,
    fallbackLanguage: "assamese",
    bcp47: "brx-IN",
  },

  // 22. Sanskrit (संस्कृतम्)
  sanskrit: {
    code: "sa",
    name: "Sanskrit",
    nativeName: "संस्कृतम्",
    script: "Devanagari",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: false,
    isDialect: false,
    fallbackLanguage: "hindi",
    bcp47: "sa-IN",
  },

  // REGIONAL DIALECTS (Not official but widely spoken)

  // Bhojpuri (भोजपुरी)
  bhojpuri: {
    code: "bho",
    name: "Bhojpuri",
    nativeName: "भोजपुरी",
    script: "Devanagari",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: true,
    fallbackLanguage: "hindi",
    bcp47: "bho-IN",
  },

  // Awadhi (अवधी)
  awadhi: {
    code: "awa",
    name: "Awadhi",
    nativeName: "अवधी",
    script: "Devanagari",
    awsTranscribeSupported: false,
    awsPollySupported: false,
    awsPollyVoice: undefined,
    bhashiniSupported: true,
    isDialect: true,
    fallbackLanguage: "hindi",
    bcp47: "awa-IN",
  },

  // English (for urban users)
  english: {
    code: "en",
    name: "English",
    nativeName: "English",
    script: "Latin",
    awsTranscribeSupported: true,
    awsPollySupported: true,
    awsPollyVoice: "Kajal", // Indian English voice
    bhashiniSupported: false,
    isDialect: false,
    bcp47: "en-IN",
  },
};

// Helper functions

export const getLanguageByCode = (code: string): LanguageConfig | undefined => {
  return Object.values(INDIAN_LANGUAGES).find((lang) => lang.code === code);
};

export const getLanguageByName = (name: string): LanguageConfig | undefined => {
  return INDIAN_LANGUAGES[name.toLowerCase()];
};

export const getSupportedLanguages = (): LanguageConfig[] => {
  return Object.values(INDIAN_LANGUAGES);
};

export const getAWSTranscribeSupportedLanguages = (): LanguageConfig[] => {
  return Object.values(INDIAN_LANGUAGES).filter((lang) => lang.awsTranscribeSupported);
};

export const getAWSPollySupportedLanguages = (): LanguageConfig[] => {
  return Object.values(INDIAN_LANGUAGES).filter((lang) => lang.awsPollySupported);
};

export const getBhashiniSupportedLanguages = (): LanguageConfig[] => {
  return Object.values(INDIAN_LANGUAGES).filter((lang) => lang.bhashiniSupported);
};

export const getOfficialLanguages = (): LanguageConfig[] => {
  return Object.values(INDIAN_LANGUAGES).filter((lang) => !lang.isDialect);
};

export const getDialects = (): LanguageConfig[] => {
  return Object.values(INDIAN_LANGUAGES).filter((lang) => lang.isDialect);
};

// Language detection helper (for future backend integration)
export const detectLanguageService = (languageCode: string): "aws" | "bhashini" | "browser" => {
  const lang = getLanguageByCode(languageCode);
  if (!lang) return "browser";

  if (lang.awsTranscribeSupported && lang.awsPollySupported) {
    return "aws";
  } else if (lang.bhashiniSupported) {
    return "bhashini";
  } else {
    return "browser";
  }
};

// Get fallback chain for a language
export const getFallbackChain = (languageCode: string): string[] => {
  const chain: string[] = [languageCode];
  let currentLang = getLanguageByCode(languageCode);

  while (currentLang?.fallbackLanguage) {
    chain.push(currentLang.fallbackLanguage);
    currentLang = getLanguageByName(currentLang.fallbackLanguage);
  }

  // Always fallback to Hindi and then English
  if (!chain.includes("hi")) chain.push("hi");
  if (!chain.includes("en")) chain.push("en");

  return chain;
};

// Priority languages for MVP (based on speaker population)
export const MVP_PRIORITY_LANGUAGES = [
  "hindi",
  "bengali",
  "telugu",
  "marathi",
  "tamil",
  "gujarati",
  "kannada",
  "malayalam",
  "punjabi",
  "english",
];

// Get display name with native script
export const getDisplayName = (languageKey: string): string => {
  const lang = INDIAN_LANGUAGES[languageKey];
  if (!lang) return languageKey;
  return `${lang.name} (${lang.nativeName})`;
};
