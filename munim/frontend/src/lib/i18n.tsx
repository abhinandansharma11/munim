import { createContext, ReactNode, useContext, useEffect, useState } from 'react';

export type Lang = 'hi' | 'en';

// Every word on screen, in simple Hindi and simple English.
const D = {
  // shared
  start: { en: 'Start', hi: 'शुरू करें' }, next: { en: 'Next', hi: 'आगे' }, skip: { en: 'Skip', hi: 'छोड़ें' },
  tapToStart: { en: 'Tap to start', hi: 'शुरू करने के लिए दबाएँ' },
  chooseLang: { en: 'Choose your language', hi: 'अपनी भाषा चुनिए' },
  // merchant
  todayEarn: { en: "Today's collection", hi: 'आज की कमाई' }, payments: { en: '{n} payments', hi: '{n} पेमेंट' },
  lastPay: { en: 'Last {amt} at {t}', hi: 'आखिरी {amt}, {t}' },
  soundbox: { en: 'Soundbox', hi: 'साउंडबॉक्स' }, working: { en: 'Working', hi: 'चालू है' }, notWorking: { en: 'Not working', hi: 'बंद है' },
  payout: { en: 'Money to bank', hi: 'बैंक में पैसा' }, stuck: { en: '{amt} stuck', hi: '{amt} रुका' }, allIn: { en: 'All received', hi: 'सब आ गया' },
  kyc: { en: 'KYC', hi: 'केवाईसी' }, kycNeeded: { en: 'Needed', hi: 'ज़रूरी है' }, kycDone: { en: 'Done', hi: 'पूरा है' },
  tapTile: { en: 'Tap any box to ask Munim', hi: 'किसी भी डिब्बे को दबाकर मुनीम से पूछें' },
  munimTitle: { en: 'Munim, your helper', hi: 'मुनीम, आपका साथी' },
  munimSub: { en: "Tell me any problem. I'll fix it for you.", hi: 'कोई भी परेशानी बताइए, मैं ठीक कर दूँगा।' },
  hello: { en: "Hello {name} ji! I'm Munim. Tap the big mic and tell me your problem, or tap one of the buttons below.",
    hi: 'नमस्ते {name} जी! मैं मुनीम हूँ। बड़ा माइक दबाकर अपनी परेशानी बताइए, या नीचे का कोई बटन दबाइए।' },
  tapSpeak: { en: 'Tap & speak', hi: 'दबाकर बोलिए' }, listeningSend: { en: 'Listening… tap to send', hi: 'सुन रहा हूँ… भेजने के लिए दबाएँ' },
  typeHere: { en: 'Or type here…', hi: 'या यहाँ लिखिए…' }, listen: { en: 'Listen', hi: 'सुनिए' },
  w_read: { en: 'Munim is reading your message', hi: 'मुनीम आपकी बात पढ़ रहा है' },
  w_listen: { en: 'Munim is listening to your voice note', hi: 'मुनीम आपकी आवाज़ सुन रहा है' },
  w_observe: { en: 'Checking your account', hi: 'आपका खाता देख रहा हूँ' }, w_think: { en: 'Thinking', hi: 'सोच रहा हूँ' },
  w_act: { en: 'Fixing it', hi: 'ठीक कर रहा हूँ' }, w_check: { en: 'Double-checking', hi: 'दोबारा जाँच रहा हूँ' },
  w_release: { en: 'Releasing your money', hi: 'आपका पैसा भेज रहा हूँ' },
  kycTitle: { en: 'Complete your KYC', hi: 'अपना केवाईसी पूरा करें' },
  kycText: { en: 'Your {amt} is on hold. It takes only 1 minute.', hi: 'आपका {amt} रुका है। सिर्फ 1 मिनट लगेगा।' },
  verifyNow: { en: 'Verify now', hi: 'अभी पूरा करें' }, verified: { en: 'Verified', hi: 'पूरा हो गया' },
  otpTitle: { en: 'Verify with Aadhaar OTP', hi: 'आधार OTP से पूरा करें' },
  otpSent: { en: 'OTP sent to your Aadhaar mobile ••••7731', hi: 'आपके आधार मोबाइल ••••7731 पर OTP भेजा गया' },
  verify: { en: 'Verify', hi: 'पूरा करें' }, demoNote: { en: 'Demo: OTP is simulated', hi: 'डेमो: OTP नकली है' },
  credited: { en: '{amt} received', hi: '{amt} आ गया' }, inBank: { en: 'in your {bank} account', hi: 'आपके {bank} खाते में' },
  noticed: { en: 'Munim noticed: {x}', hi: 'मुनीम ने देखा: {x}' }, viaSoundbox: { en: 'via Soundbox', hi: 'साउंडबॉक्स से' },
  voiceNote: { en: 'Voice note', hi: 'आवाज़ संदेश' }, help: { en: 'How it works', hi: 'कैसे चलता है' },
  voiceOn: { en: 'Munim will speak replies', hi: 'मुनीम जवाब बोलकर सुनाएगा' }, voiceOff: { en: 'Voice off', hi: 'आवाज़ बंद' },
  micHttps: { en: 'Opening the phone recorder instead', hi: 'फ़ोन का रिकॉर्डर खोल रहे हैं' },
  micNothing: { en: "I didn't catch that. Try again, a little closer.", hi: 'सुनाई नहीं दिया। फिर से, थोड़ा पास से बोलिए।' },
  micBlocked: { en: 'Microphone is blocked. Allow it, or type instead.', hi: 'माइक बंद है। अनुमति दें, या लिखकर भेजें।' },
  payToast: { en: '{amt} received', hi: '{amt} प्राप्त हुए' },
  payMissed: { en: "{amt} received, but the Soundbox is off so it didn't announce", hi: '{amt} आए, पर साउंडबॉक्स बंद होने से आवाज़ नहीं आई' },
  kycDoneToast: { en: 'KYC complete', hi: 'केवाईसी पूरा हुआ' },
  tabHome: { en: 'Home', hi: 'होम' }, tabMunim: { en: 'Munim', hi: 'मुनीम' }, tabQR: { en: 'My QR', hi: 'मेरा QR' },
  nextSettle: { en: 'Next settlement', hi: 'अगला पैसा बैंक में' }, settleWhen: { en: 'tomorrow 9 am', hi: 'कल सुबह 9 बजे' },
  askMunim: { en: 'Ask Munim', hi: 'मुनीम से पूछिए' }, askMunimSub: { en: 'Any problem, in Hindi or English. He fixes it.', hi: 'कोई भी परेशानी, हिंदी या अंग्रेज़ी में। वो ठीक कर देगा।' },
  yourBiz: { en: 'Your business', hi: 'आपका कारोबार' }, recentPay: { en: 'Recent payments', hi: 'हाल के पेमेंट' },
  noPayments: { en: 'No payments yet today.', hi: 'आज अभी तक कोई पेमेंट नहीं।' }, pendingPay: { en: 'Pending at bank', hi: 'बैंक में अटका' },
  scanPay: { en: 'Scan with any UPI app to pay', hi: 'किसी भी UPI ऐप से स्कैन करके पेमेंट करें' }, acceptsAll: { en: 'Paytm and all UPI apps accepted', hi: 'Paytm और सभी UPI ऐप चलते हैं' },
  // onboarding
  ob1t: { en: "Namaste! I'm Munim", hi: 'नमस्ते! मैं मुनीम हूँ' },
  ob1b: { en: 'Your digital munim on Paytm. I look after your payments, your money to the bank and your Soundbox.',
    hi: 'पेटीएम पर आपका डिजिटल मुनीम। मैं आपके पेमेंट, बैंक के पैसे और साउंडबॉक्स का ध्यान रखता हूँ।' },
  ob2t: { en: 'Just speak', hi: 'बस बोलिए' },
  ob2b: { en: 'Tap the big mic and say your problem in Hindi or English, like you would to a person.',
    hi: 'बड़ा माइक दबाइए और अपनी परेशानी हिंदी या अंग्रेज़ी में बोलिए, जैसे किसी इंसान से बोलते हैं।' },
  ob3t: { en: 'I fix it myself', hi: 'मैं खुद ठीक करूँगा' },
  ob3b: { en: "I check your account, fix the problem and tell you when it's done. For big money, a Paytm person checks first.",
    hi: 'मैं आपका खाता देखकर परेशानी खुद ठीक करूँगा और बताऊँगा। बड़ी रकम के लिए पेटीएम का एक साथी पहले जाँच करेगा।' },
  // soundbox
  online: { en: 'Online', hi: 'चालू' }, offline: { en: 'Offline', hi: 'बंद' },
  sbAsk: { en: 'Tap & ask Munim', hi: 'दबाइए और मुनीम से पूछिए' }, sbSend: { en: 'Tap to send', hi: 'भेजने के लिए दबाएँ' },
  sbIntro: { en: 'Payments are announced here. Tap the button and ask Munim anything.', hi: 'यहाँ पेमेंट की आवाज़ आती है। बटन दबाकर मुनीम से कुछ भी पूछिए।' },
  sbReady: { en: 'READY', hi: 'तैयार' }, sbReceived: { en: 'RECEIVED', hi: 'प्राप्त' }, sbNoNet: { en: 'NO NETWORK', hi: 'नेटवर्क नहीं' },
  sbListening: { en: 'LISTENING', hi: 'सुन रहा' }, sbSpeaking: { en: 'SPEAKING', hi: 'बोल रहा' }, sbThinking: { en: 'THINKING', hi: 'सोच रहा' },
  sbMissed: { en: 'A {amt} payment came, but the Soundbox is off, so it stayed silent.', hi: '{amt} का पेमेंट आया, पर साउंडबॉक्स बंद होने से आवाज़ नहीं आई।' },
  sbAsked: { en: 'You asked: “{q}”', hi: 'आपने पूछा: “{q}”' }, sbUnlock: { en: 'Tap once so the Soundbox can speak.', hi: 'एक बार दबाइए ताकि साउंडबॉक्स बोल सके।' },
  // rep
  repSub: { en: 'Field sales, Indore', hi: 'फील्ड सेल्स, इंदौर' }, newBriefs: { en: 'New briefs from Munim', hi: 'मुनीम से नए लीड' },
  visits: { en: 'Visits booked', hi: 'तय मुलाकातें' }, leads: { en: 'Leads', hi: 'लीड' },
  noLeads: { en: 'No leads yet', hi: 'अभी कोई लीड नहीं' },
  noLeadsSub: { en: "When Munim spots a real opportunity while solving a shop's problem, the brief appears here.",
    hi: 'जब मुनीम किसी दुकान की परेशानी हल करते समय अच्छा मौका देखेगा, उसकी जानकारी यहाँ आएगी।' },
  call: { en: 'Call', hi: 'कॉल करें' }, route: { en: 'Add to route', hi: 'रूट में जोड़ें' }, briefBy: { en: 'Written by Munim', hi: 'मुनीम ने लिखा' },
  newLead: { en: 'New lead from Munim', hi: 'मुनीम से नया लीड' }, visitBooked: { en: 'Visit booked', hi: 'मुलाकात तय' }, isNew: { en: 'New', hi: 'नया' },
  // console
  desk: { en: 'Merchant desk', hi: 'मर्चेंट डेस्क' }, liveCases: { en: 'Live cases', hi: 'चल रहे मामले' },
  noCases: { en: 'No cases yet. Speak to Munim from the merchant phone.', hi: 'अभी कोई मामला नहीं। दुकानदार के फ़ोन से मुनीम से बात करें।' },
  waiting: { en: 'Waiting for a shopkeeper', hi: 'दुकानदार का इंतज़ार' },
  waitingSub: { en: 'When a shopkeeper talks to Munim, you will see every step it takes here, live.', hi: 'जब कोई दुकानदार मुनीम से बात करेगा, उसका हर कदम यहाँ दिखेगा।' },
  today: { en: 'Today', hi: 'आज' }, kSolved: { en: 'Problems solved', hi: 'हल हुई परेशानियाँ' }, kTime: { en: 'Avg time to fix', hi: 'ठीक करने का औसत समय' },
  kBlocked: { en: 'Unsafe actions stopped', hi: 'रोके गए गलत काम' }, kLeads: { en: 'Sales leads sent', hi: 'भेजे गए सेल्स लीड' },
  activity: { en: 'Activity log', hi: 'काम का रिकॉर्ड' }, nothingYet: { en: 'Nothing yet.', hi: 'अभी कुछ नहीं।' },
  observe: { en: 'Observe', hi: 'देखना' }, think: { en: 'Think', hi: 'सोचना' }, act: { en: 'Act', hi: 'करना' }, check: { en: 'Check', hi: 'जाँचना' },
  s_open: { en: 'Working', hi: 'चल रहा' }, s_resolved: { en: 'Solved', hi: 'हल हुआ' }, s_waiting_merchant: { en: 'Waiting for shopkeeper', hi: 'दुकानदार का इंतज़ार' },
  s_waiting_human: { en: 'Needs your OK', hi: 'मंज़ूरी चाहिए' }, s_handed_over: { en: 'With a teammate', hi: 'साथी के पास' },
  t_read: { en: 'Just looked', hi: 'सिर्फ देखा' }, t_auto: { en: 'Did it itself', hi: 'खुद किया' }, t_merchant: { en: 'With shopkeeper', hi: 'दुकानदार के साथ' },
  t_human: { en: 'Needs a person', hi: 'इंसान की मंज़ूरी' }, stopped: { en: 'Stopped by safety check', hi: 'सुरक्षा जाँच ने रोका' },
  pending: { en: 'Waiting for your OK', hi: 'आपकी मंज़ूरी का इंतज़ार' }, undone: { en: 'Undone', hi: 'वापस लिया' },
  told: { en: 'Told the shopkeeper', hi: 'दुकानदार को बताया' }, thinks: { en: 'Munim thinks', hi: 'मुनीम सोचता है' },
  needsOk: { en: 'Needs your OK', hi: 'आपकी मंज़ूरी चाहिए' }, neverAlone: { en: 'Munim never moves this much money on its own', hi: 'मुनीम इतनी बड़ी रकम खुद कभी नहीं भेजता' },
  approve: { en: 'Approve', hi: 'मंज़ूर करें' }, handle: { en: "I'll handle it", hi: 'मैं खुद देखूँगा' }, undo: { en: 'Undo', hi: 'वापस लें' },
  approver: { en: 'Approver', hi: 'मंज़ूरी देने वाले' }, demo: { en: 'Demo', hi: 'डेमो' },
  approvedBy: { en: 'Approved by {n}', hi: '{n} ने मंज़ूर किया' }, undoneToast: { en: 'Undone. The log shows who did it.', hi: 'वापस लिया। रिकॉर्ड में नाम दर्ज है।' },
  foundBy: { en: 'Found by Munim', hi: 'मुनीम ने खुद देखा' }, app: { en: 'Merchant app', hi: 'मर्चेंट ऐप' },
  // fraud network
  alertTitle: { en: 'Fraud alert in your area', hi: 'आपके इलाके में फ्रॉड अलर्ट' },
  alertBy: { en: 'Munim network watch', hi: 'मुनीम की नेटवर्क निगरानी' },
  sbAlert: { en: 'ALERT', hi: 'सावधान' },
  sbNewAlert: { en: 'New alert! Tap to listen', hi: 'नया अलर्ट! सुनने के लिए दबाएँ' },
  dFraud: { en: 'Fake ₹2,000 claims at 2 shops', hi: '2 दुकानों पर नकली ₹2,000' },
  fTitle: { en: 'Fraud alert demo: 3 shops, one area', hi: 'फ्रॉड अलर्ट डेमो: एक इलाके की 3 दुकानें' },
  fSub: { en: 'Shops 1 and 2 ask "Did Rohit\'s ₹2,000 come?". When 2 shops report it, Munim warns every shop in Vijay Nagar. Shop 3\'s Soundbox speaks the alert on its own.',
    hi: 'दुकान 1 और 2 पूछें "रोहित ने ₹2,000 भेजा, आया क्या?"। 2 दुकानों से एक जैसी शिकायत आते ही मुनीम विजय नगर की हर दुकान को सावधान करता है। दुकान 3 का साउंडबॉक्स अपने आप बोलता है।' },
  fApp: { en: 'App', hi: 'ऐप' }, fBox: { en: 'Soundbox', hi: 'साउंडबॉक्स' },
  // sign-up + sales
  qJoin: { en: 'New shopkeeper', hi: 'नया दुकानदार' }, qJoinSub: { en: 'Join Paytm by talking', hi: 'बोलकर पेटीएम से जुड़ें' },
  sales: { en: 'Sales by Munim', hi: 'मुनीम से बिक्री' }, sNew: { en: 'new shops', hi: 'नई दुकानें' },
  sAvg: { en: 'avg {m} min to go live', hi: 'चालू होने में औसत {m} मिनट' }, sLeads: { en: 'leads', hi: 'लीड' }, sVisits: { en: 'visits', hi: 'मुलाकातें' },
  sbComing: { en: 'Coming tomorrow', hi: 'कल लगेगा' },
  // cost panel
  cTitle: { en: 'Cost per problem solved', hi: 'एक परेशानी हल करने का खर्च' },
  cMunim: { en: 'Munim', hi: 'मुनीम' }, cPerson: { en: 'Support call by a person', hi: 'इंसान से सपोर्ट कॉल' },
  cSaved: { en: 'Saved today', hi: 'आज की बचत' }, cFast: { en: 'needed no AI call', hi: 'बिना AI कॉल के हल' },
  cPrevented: { en: 'fixed before the shopkeeper called', hi: 'दुकानदार के कॉल से पहले ठीक' },
  dMode: { en: 'AI mode', hi: 'AI मोड' }, dSaver: { en: 'Saver', hi: 'बचत' }, dSaverSub: { en: 'Routine asks on the fast path, AI for the rest', hi: 'आम सवाल तेज़ रास्ते से, बाकी AI से' },
  dAlways: { en: 'Always AI', hi: 'हमेशा AI' }, dAlwaysSub: { en: 'Every message goes to the AI model', hi: 'हर संदेश AI मॉडल को' },
  // demo drawer
  dSim: { en: 'Make something happen', hi: 'कुछ घटना करवाएँ' }, dPay: { en: 'Customer pays ₹500', hi: 'ग्राहक ₹500 देता है' },
  dOff: { en: 'Soundbox goes offline', hi: 'साउंडबॉक्स बंद हो जाता है' }, dTwice: { en: 'Customer charged twice', hi: 'ग्राहक से दो बार पैसे कटे' },
  dClose: { en: 'Shop closes', hi: 'दुकान बंद होती है' }, dType: { en: 'Type as the shopkeeper', hi: 'दुकानदार बनकर लिखें' },
  dKey: { en: 'Sarvam AI key', hi: 'सर्वम AI की चाबी' }, dKeyPh: { en: 'Paste your Sarvam API key', hi: 'अपनी सर्वम API की चाबी यहाँ डालें' },
  dSave: { en: 'Save & test', hi: 'सेव करके जाँचें' }, dVoice: { en: 'Voice', hi: 'आवाज़' }, dBrain: { en: 'AI brain', hi: 'AI दिमाग' },
  dKeySet: { en: 'Key saved: {k}', hi: 'चाबी सेव है: {k}' }, dNoKey: { en: 'No key yet. Munim runs on its offline brain.', hi: 'अभी चाबी नहीं। मुनीम ऑफ़लाइन चल रहा है।' },
  dReset: { en: 'Reset demo', hi: 'डेमो फिर से शुरू' }, dResetSure: { en: 'Tap again to reset', hi: 'पक्का? फिर दबाएँ' },
  dPhones: { en: 'Open on phones (QR codes)', hi: 'फ़ोन पर खोलें (QR कोड)' }, dResetDone: { en: 'Fresh demo data loaded', hi: 'नया डेमो डेटा लोड हुआ' },
  // start page
  sTitle: { en: 'Munim', hi: 'मुनीम' },
  sHero1: { en: 'Every shop gets', hi: 'हर दुकान का' }, sHero2: { en: 'its own munim.', hi: 'अपना मुनीम।' },
  sLead: { en: "An AI teammate for Paytm's merchant desk. It hears shopkeepers in Hindi or English, fixes their problems itself, and asks a person before risky steps.",
    hi: 'पेटीएम के मर्चेंट डेस्क का AI साथी। यह दुकानदारों की बात हिंदी या अंग्रेज़ी में सुनता है, परेशानी खुद ठीक करता है, और जोखिम वाले काम से पहले इंसान से पूछता है।' },
  sHow: { en: 'Try it on your phone', hi: 'अपने फ़ोन पर चलाकर देखें' },
  sStep1: { en: 'Connect your phone to the same Wi-Fi or hotspot as this laptop.', hi: 'अपने फ़ोन को इसी लैपटॉप वाले वाई-फ़ाई या हॉटस्पॉट से जोड़ें।' },
  sStep2: { en: 'Scan a QR code below with the phone camera.', hi: 'नीचे का QR कोड फ़ोन के कैमरे से स्कैन करें।' },
  sStep3: { en: 'If you see a warning, tap Advanced, then Proceed. Allow the microphone.', hi: 'चेतावनी दिखे तो Advanced, फिर Proceed दबाएँ। माइक की अनुमति दें।' },
  qMerchant: { en: 'Shopkeeper app', hi: 'दुकानदार ऐप' }, qMerchantSub: { en: 'Talk to Munim, see your money', hi: 'मुनीम से बात करें, पैसा देखें' },
  qSoundbox: { en: 'Soundbox', hi: 'साउंडबॉक्स' }, qSoundboxSub: { en: 'Put it on the counter', hi: 'काउंटर पर रखें' },
  qRep: { en: 'Field rep', hi: 'फील्ड रिप' }, qRepSub: { en: 'Gets sales leads', hi: 'सेल्स लीड पाता है' },
  qConsole: { en: 'Paytm desk', hi: 'पेटीएम डेस्क' }, qConsoleSub: { en: 'Open this on the laptop or projector', hi: 'इसे लैपटॉप या प्रोजेक्टर पर खोलें' },
  openHere: { en: 'Open here', hi: 'यहीं खोलें' },
};
export type Key = keyof typeof D;

const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: (k: Key, v?: Record<string, string | number>) => string }>(null!);

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    try { return (localStorage.getItem('munim-lang') as Lang) || 'hi'; } catch { return 'hi'; }
  });
  const setLang = (l: Lang) => { setLangState(l); try { localStorage.setItem('munim-lang', l); } catch {} };
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  const t = (k: Key, v: Record<string, string | number> = {}) =>
    Object.entries(v).reduce((s, [a, b]) => s.replace(`{${a}}`, String(b)), D[k][lang]);
  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>;
}
export const useLang = () => useContext(Ctx);

// What a message says in the chosen language. Munim's replies carry Hindi (speak) and English (en) versions.
export function pick(m: { text?: string; speak?: string | null; en?: string | null }, lang: Lang) {
  return (lang === 'hi' ? m.speak : m.en) || m.text || '';
}

// Hindi names for Munim's tools, for the desk screen.
export const TOOL_HI: Record<string, string> = {
  get_merchant_profile: 'दुकान की जानकारी देखी', get_device_health: 'साउंडबॉक्स जाँचा', get_settlements: 'बैंक भुगतान देखे',
  get_kyc_status: 'केवाईसी देखा', search_payments: 'पेमेंट खोजे', verify_payment: 'पेमेंट की पुष्टि', get_today_summary: 'आज का हिसाब',
  check_loan_eligibility: 'लोन की पात्रता देखी', renew_device_plan: 'साउंडबॉक्स प्लान रिन्यू किया', send_kyc_link: 'केवाईसी लिंक भेजा',
  requeue_settlement: 'रुका पैसा भेजा', initiate_refund: 'रिफंड', create_lead_brief: 'फील्ड रिप को लीड भेजा', book_field_visit: 'मुलाकात तय की',
  order_device: 'डिवाइस ऑर्डर किया', handover_to_human: 'साथी को सौंपा',
  get_sales: 'बिक्री का हिसाब देखा', get_recent_payments: 'हाल के पेमेंट देखे', get_payout_summary: 'बैंक में भेजा पैसा देखा',
  get_refund_status: 'रिफंड देखे', check_transaction_status: 'अटके पेमेंट देखे', verify_bank_account: 'बैंक खाते में ₹1 भेजकर नाम जाँचा', run_onboarding_checks: 'साइन-अप की जाँच', activate_merchant: 'दुकान पेटीएम पर चालू की', create_fraud_report: 'फ्रॉड रिपोर्ट बनाई', alert_area_shops: 'इलाके की सभी दुकानों को सावधान किया', explain_settlement: 'पेआउट की कटौती देखी',
};
