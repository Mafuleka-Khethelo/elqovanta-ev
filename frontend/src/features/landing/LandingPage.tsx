import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUpRight, Check, ChevronDown, Clock3, MapPin, Menu, MessageCircle, Pause, Play, PlugZap, ShieldCheck, X, Zap } from "lucide-react";
import { useAuth } from "../../app/providers";
import { BrandLogo } from "../../components/BrandLogo";
import { useLandingMotion } from "./useLandingMotion";
import "./landing.css";

const vehicles = [
  { src: "/cars/teal-coupe.png", alt: "Deep teal electric coupe", color: "#17686B", label: "The open-road kind" },
  { src: "/cars/yellow-city.png", alt: "Sunshine yellow electric city car", color: "#EDBC24", label: "The everyday-adventure kind" },
  { src: "/cars/crimson-fastback.png", alt: "Crimson electric fastback", color: "#B72B36", label: "The take-the-long-way kind" },
  { src: "/cars/silver-crossover.png", alt: "Silver electric crossover", color: "#A0A6A5", label: "The bring-everyone kind" },
  { src: "/cars/ivory-pickup.png", alt: "Ivory electric pickup", color: "#D2CAB8", label: "The go-somewhere-new kind" },
];

const steps = [
  { title: "Find your next stop.", text: "Explore participating stations. Check their reported status, connectors and location before you set off." },
  { title: "Take your place.", text: "Join a first-come waiting list. Follow your position and receive an offer when an app slot opens." },
  { title: "Keep life moving.", text: "Report your session, stay in touch with the station, and keep your charging history together." },
];

const faqs = [
  { question: "What is Elqovanta EV?", answer: "Elqovanta EV brings charger discovery, waiting lists, session records and station messages together. It helps participating drivers and station teams coordinate their charging stops." },
  { question: "How does the waiting list work?", answer: "Join a participating station's waiting list and follow your place. When a configured app slot becomes free, the next eligible driver gets an offer with ten minutes to accept. You can be in one waiting list or one active session at a time." },
  { question: "Does joining reserve a physical charging bay?", answer: "A waiting-list offer coordinates people using Elqovanta EV. It does not reserve a physical bay. Station status is reported by drivers and managers, so check the latest update and follow the station's instructions when you arrive." },
  { question: "How do I get started?", answer: "Create a driver account, sign in, and find a participating station. You can save favourites, join a waiting list, report your session and message an assigned station manager from your account." },
  { question: "I manage a station. Can I use Elqovanta EV?", answer: "Station managers have their own workspace for assigned chargers, reported status, capacity, waiting lists and driver messages. Manager access is issued by the operator. If you already have a manager account, use Sign in." },
];

function Brand() {
  return <Link to="/" className="cc-brand" aria-label="Elqovanta EV home">
    <BrandLogo />
  </Link>;
}

function JourneyPreview({ step }: { step: number }) {
  return <div className={`cc-journey-preview cc-preview-${step}`}>
    <div className="cc-preview-top"><span><span className="cc-dot" /> A look inside</span><span>Illustrative preview</span></div>
    {step === 0 ? <div className="cc-map-preview">
      <svg className="cc-map-roads" viewBox="0 0 600 440" fill="none" aria-hidden="true">
        <path d="M-30 88L630 350M-20 365L635 110M83-30L270 470M395-30L510 470" stroke="#FFF" strokeWidth="24" />
        <path d="M-30 88L630 350M-20 365L635 110M83-30L270 470M395-30L510 470" stroke="#CFD7CA" strokeWidth="1" />
        <path d="M120 373L227 274L309 240L363 182" stroke="#638B77" strokeWidth="4" strokeDasharray="7 8" />
      </svg>
      <span className="cc-map-area cc-map-area-one">YOUR NEXT STOP</span><span className="cc-map-area cc-map-area-two">THE ROAD AHEAD</span>
      <span className="cc-map-location"><span /></span>
      <span className="cc-map-pin cc-map-pin-main"><PlugZap size={25} /></span>
      <span className="cc-map-pin cc-map-pin-other"><PlugZap size={19} /></span>
      <div className="cc-map-station"><span className="cc-station-icon"><PlugZap size={22} /></span><div><strong>Your chosen station</strong><span>Location. Connectors. Reported status.</span></div><ArrowUpRight size={20} /></div>
    </div> : step === 1 ? <div className="cc-queue-preview">
      <div className="cc-preview-round"><Clock3 size={35} strokeWidth={1.5} /></div>
      <h3>Your turn.<br />Made clear.</h3><p>A little clarity for the time in between.</p>
      <div className="cc-queue-track"><span><Check size={16} /> Join the list</span><i /><span>Get an offer</span><i /><span>Plug in</span></div>
      <div className="cc-preview-notice"><span className="cc-dot" /><span>Updates, right where you need them.</span><MessageCircle size={18} /></div>
    </div> : <div className="cc-session-preview">
      <div className="cc-session-orbit"><span /><span /><div><PlugZap size={36} strokeWidth={1.5} /><strong>All connected.</strong><small>Your session, in one place.</small></div></div>
      <div className="cc-preview-session-labels"><span><i /> Connected</span><span><i /> Charging</span><span><i /> Ready to go</span></div>
    </div>}
    <div className="cc-preview-bottom"><span>Less to juggle. More to enjoy.</span><Zap size={16} /></div>
  </div>;
}

export function LandingPage() {
  const root = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [vehicle, setVehicle] = useState(0);
  const [activeStep, setActiveStep] = useState(0);
  const [station, setStation] = useState("");
  const [connector, setConnector] = useState("");
  const [openFaq, setOpenFaq] = useState<number | null>(0);
  const [paused, setPaused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const motionEnabled = !paused && !reducedMotion;
  const manager = user?.role === "manager";
  const accountHref = user ? manager ? "/app/manage" : user.role === "researcher" ? "/app/research/predict" : "/app" : "/register";
  const currentCar = vehicles[vehicle];
  useLandingMotion(root, motionEnabled);

  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(preference.matches);
    preference.addEventListener("change", update);
    return () => preference.removeEventListener("change", update);
  }, []);

  function findCharger(event: FormEvent) {
    event.preventDefault();
    const query = new URLSearchParams();
    if (station.trim()) query.set("q", station.trim());
    if (connector) query.set("port", connector);
    navigate(`/app/chargers${query.size ? `?${query}` : ""}`);
  }

  function changeStep(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? 0 : event.key === "End" ? steps.length - 1 : (index + (event.key === "ArrowDown" ? 1 : -1) + steps.length) % steps.length;
    setActiveStep(next);
    document.getElementById(`cc-step-${next}`)?.focus();
  }

  return <div ref={root} className={`cc-home${motionEnabled ? "" : " cc-motion-paused"}`}>
    <a className="cc-skip" href="#cc-main">Skip to content</a>
    <header className="cc-header">
      <div className="cc-nav cc-wrap">
        <Brand />
        <nav id="cc-navigation" className={`cc-nav-links${menuOpen ? " is-open" : ""}`} aria-label="Main navigation" onKeyDown={(event) => { if (event.key === "Escape") { setMenuOpen(false); document.getElementById("cc-menu-toggle")?.focus(); } }}>
          <a href="#how-it-works" onClick={() => setMenuOpen(false)}>How it works</a>
          <a href="#for-drivers" onClick={() => setMenuOpen(false)}>For drivers</a>
          <a href="#for-stations" onClick={() => setMenuOpen(false)}>For stations</a>
          <a href="#questions" onClick={() => setMenuOpen(false)}>FAQs</a>
          <Link className="cc-mobile-sign-in" to="/sign-in" onClick={() => setMenuOpen(false)}>Sign in <ArrowUpRight size={16} /></Link>
        </nav>
        <div className="cc-nav-actions">
          {!user ? <Link className="cc-sign-in" to="/sign-in">Sign in</Link> : null}
          <Link className="cc-button cc-button-small" to={accountHref}>{user ? "My dashboard" : "Get started"}<ArrowUpRight size={16} /></Link>
          <button id="cc-menu-toggle" className="cc-menu-toggle" type="button" aria-label={menuOpen ? "Close menu" : "Open menu"} aria-expanded={menuOpen} aria-controls="cc-navigation" onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={23} /> : <Menu size={23} />}</button>
        </div>
      </div>
    </header>

    <main id="cc-main" tabIndex={-1}>
      <section className="cc-hero" aria-labelledby="cc-hero-title">
        <div className="cc-hero-grid cc-wrap">
          <div className="cc-hero-copy">
            <p className="cc-eyebrow cc-hero-eyebrow"><span className="cc-dot" /> GOOD ENERGY. GREAT JOURNEYS.</p>
            <h1 id="cc-hero-title"><span><span>Less waiting.</span></span><span><span className="cc-hero-second">More living.</span></span></h1>
            <p className="cc-hero-description">Find your charging stop. Take your place.<br className="cc-desktop-break" /> Get on with the good stuff.</p>
            <a className="cc-button cc-button-lime cc-hero-cta" href="#find-charge">Find a charger <ArrowUpRight size={20} /></a>
            <a className="cc-hero-how" href="#how-it-works"><span><ArrowDown size={15} /></span>A simpler way to charge</a>
          </div>
          <div className="cc-hero-scene" aria-label="Electric vehicle showcase">
            <div className="cc-hero-disc" aria-hidden="true"><span className="cc-disc-type">GOOD<br />TO GO.</span></div>
            <svg className="cc-hero-orbit" viewBox="0 0 600 600" fill="none" aria-hidden="true"><circle cx="300" cy="300" r="275" stroke="currentColor" strokeWidth="1" /><circle cx="300" cy="300" r="275" stroke="currentColor" strokeWidth="3" strokeDasharray="18 1710" className="cc-orbit-spark" /></svg>
            <span className="cc-scene-caption"><span className="cc-dot" /> ALL ELECTRIC. ALL YOU.</span>
            <div className="cc-hero-car-depth"><img key={currentCar.src} className="cc-hero-car" src={currentCar.src} alt={currentCar.alt} width="1536" height="1024" fetchPriority="high" /></div>
            <div className="cc-energy-badge" aria-hidden="true"><Zap size={24} fill="currentColor" /><span>Good things<br />are charging.</span></div>
            <div className="cc-vehicle-controls">
              <div><span className="cc-vehicle-label">{currentCar.label}</span><span className="cc-vehicle-count">0{vehicle + 1}<span> / 05</span></span></div>
              <div className="cc-vehicle-swatches" aria-label="Choose a vehicle illustration">{vehicles.map((car, index) => <button key={car.src} type="button" className={vehicle === index ? "is-active" : ""} aria-label={`Show ${car.alt.toLowerCase()}`} aria-pressed={vehicle === index} onClick={() => setVehicle(index)}><span style={{ backgroundColor: car.color }} /></button>)}</div>
              <div className="cc-vehicle-arrows"><button type="button" aria-label="Previous vehicle" onClick={() => setVehicle((vehicle + vehicles.length - 1) % vehicles.length)}><ArrowLeft size={18} /></button><button type="button" aria-label="Next vehicle" onClick={() => setVehicle((vehicle + 1) % vehicles.length)}><ArrowRight size={18} /></button></div>
            </div>
          </div>
        </div>

        <div id="find-charge" className="cc-search-wrap cc-wrap">
          <div className="cc-search-heading"><span>YOUR NEXT GOOD STOP STARTS HERE.</span><span><PlugZap size={15} /> A little more connected.</span></div>
          {manager ? <div className="cc-search cc-manager-search"><div><strong>Your station workspace</strong><span>Chargers, waiting lists and driver conversations, together.</span></div><Link className="cc-button" to="/app/manage">Open dashboard <ArrowUpRight size={19} /></Link></div> : <form className="cc-search" onSubmit={findCharger}>
            <label className="cc-search-station"><MapPin size={22} strokeWidth={1.5} /><span><span className="cc-field-label">Where are you heading?</span><input aria-label="Search station name" placeholder="Search a station name" value={station} onChange={(event) => setStation(event.target.value)} maxLength={200} /></span></label>
            <label className="cc-search-connector"><PlugZap size={21} strokeWidth={1.5} /><span><span className="cc-field-label">Your connection</span><select aria-label="Connector type" value={connector} onChange={(event) => setConnector(event.target.value)}><option value="">Any connector</option><option value="Level 1">Level 1</option><option value="Level 2">Level 2</option></select></span><ChevronDown size={15} /></label>
            <button className="cc-button" type="submit">Find a charger <ArrowUpRight size={20} /></button>
          </form>}
          <div className="cc-search-note"><span><ShieldCheck size={14} /> Station status reported by drivers and managers.</span><span>One account. A more connected journey.</span></div>
        </div>
      </section>

      <section id="how-it-works" className="cc-how cc-wrap cc-section">
        <div className="cc-section-intro" data-reveal><div><p className="cc-eyebrow">A BETTER WAY TO PLUG IN</p><h2>A little clarity.<br />A lot more freedom.</h2></div><p>Charging should fit around your life.<br />We bring the little details together, so you<br className="cc-desktop-break" /> can focus on wherever you’re going.</p></div>
        <div className="cc-how-grid">
          <div className="cc-steps" role="tablist" aria-label="Explore how Elqovanta EV works" aria-orientation="vertical" data-reveal>{steps.map((step, index) => <button key={step.title} id={`cc-step-${index}`} type="button" role="tab" aria-selected={activeStep === index} aria-controls="cc-journey-panel" tabIndex={activeStep === index ? 0 : -1} onKeyDown={(event) => changeStep(event, index)} onClick={() => setActiveStep(index)} className={`cc-step${activeStep === index ? " is-active" : ""}`}><span className="cc-step-number">0{index + 1}</span><span className="cc-step-copy"><span className="cc-step-title">{step.title}</span><span className="cc-step-description">{step.text}</span></span><ArrowUpRight className="cc-step-arrow" size={22} /></button>)}</div>
          <div id="cc-journey-panel" role="tabpanel" aria-labelledby={`cc-step-${activeStep}`} tabIndex={0} data-reveal><JourneyPreview key={activeStep} step={activeStep} /></div>
        </div>
      </section>

      <section id="for-drivers" className="cc-drivers">
        <div className="cc-drivers-grid cc-wrap">
          <div className="cc-drivers-art" data-reveal><span className="cc-art-label">FOR YOUR EVERYDAY. AND YOUR SOMEDAY.</span><span className="cc-drivers-type" aria-hidden="true">LET’S<br />GO.</span><img src="/cars/yellow-city.png" alt="A bright yellow electric city car" width="1536" height="1024" loading="lazy" /><span className="cc-art-footnote"><Zap size={17} fill="currentColor" /> Bring your kind of energy.</span></div>
          <div className="cc-drivers-copy" data-reveal><p className="cc-eyebrow">MADE FOR THE WAY YOU MOVE</p><h2>Your day.<br />Your drive.<br /><span>All connected.</span></h2><p>The daily commute. The coffee detour. The long way home. Keep your charging plans together, whatever the day has in mind.</p><ul className="cc-benefits"><li><Check size={16} /><span>Your favourite stations, saved.</span></li><li><Check size={16} /><span>Your place in line, easy to follow.</span></li><li><Check size={16} /><span>Your sessions and messages, in one place.</span></li></ul><Link className="cc-text-link" to={accountHref}>{user ? "Back to your dashboard" : "Make your next stop simpler"}<span><ArrowUpRight size={20} /></span></Link></div>
        </div>
      </section>

      <section id="for-stations" className="cc-stations">
        <div className="cc-stations-grid cc-wrap">
          <div className="cc-stations-copy" data-reveal><p className="cc-eyebrow"><span className="cc-dot" /> GOOD ENERGY TAKES A TEAM</p><h2>Behind every plug.<br />People who care.</h2><p>A calmer workspace for station teams. Keep your chargers, waiting lists and driver conversations moving together.</p><div className="cc-station-features"><span><PlugZap size={18} /> Station updates</span><span><Clock3 size={18} /> Queue coordination</span><span><MessageCircle size={18} /> Driver messages</span></div><Link className="cc-button cc-button-lime" to={manager ? "/app/manage" : "/sign-in"}>Station manager sign in <ArrowUpRight size={19} /></Link><small>Manager accounts are issued by the operator.</small></div>
          <div className="cc-stations-art" data-reveal><div className="cc-station-orbit" aria-hidden="true" /><div className="cc-station-pylon" aria-hidden="true"><div><Zap size={19} fill="currentColor" /><span>Elqovanta EV</span></div><span className="cc-pylon-screen"><PlugZap size={27} /><i /><i /></span><span className="cc-pylon-port" /><span className="cc-pylon-cable" /></div><img src="/cars/crimson-fastback.png" alt="A crimson electric car beside a stylised charging station" width="1536" height="1024" loading="lazy" /><span className="cc-station-art-caption">A BETTER STOP IS A TEAM EFFORT.</span></div>
        </div>
      </section>

      <section id="questions" className="cc-faq cc-wrap cc-section">
        <div className="cc-faq-heading" data-reveal><p className="cc-eyebrow">A FEW GOOD ANSWERS</p><h2>Good questions.<br />Clear answers.</h2><p>A little more to know before you go.</p><span className="cc-faq-symbol" aria-hidden="true"><MessageCircle size={34} strokeWidth={1.3} /></span></div>
        <div className="cc-faq-list" data-reveal>{faqs.map((faq, index) => <div className={`cc-faq-item${openFaq === index ? " is-open" : ""}`} key={faq.question}><h3><button type="button" id={`cc-faq-question-${index}`} aria-expanded={openFaq === index} aria-controls={`cc-faq-answer-${index}`} onClick={() => setOpenFaq(openFaq === index ? null : index)}><span>{faq.question}</span><span className="cc-faq-plus" aria-hidden="true" /></button></h3><div id={`cc-faq-answer-${index}`} role="region" aria-labelledby={`cc-faq-question-${index}`} hidden={openFaq !== index}><p>{faq.answer}</p></div></div>)}</div>
      </section>

      <section className="cc-final-section cc-wrap" data-reveal><div className="cc-final"><div className="cc-final-rings" aria-hidden="true"><i /><i /><i /></div><div><p className="cc-eyebrow">THE ROAD AHEAD IS YOURS</p><h2>Go make<br />a good day.</h2><p>We’ll help you find your next charging stop.</p></div><Link className="cc-final-action" to={accountHref}><span>{user ? "Open your dashboard" : "Let’s get you going"}</span><span><ArrowUpRight size={43} strokeWidth={1.4} /></span></Link></div></section>
    </main>

    <footer className="cc-footer cc-wrap"><div className="cc-footer-top"><Brand /><p>A little less waiting.<br />A little more living.</p><div><a href="#how-it-works">How it works</a><a href="#for-stations">For stations</a><a href="#questions">FAQs</a></div><Link className="cc-text-link" to={accountHref}>{user ? "My dashboard" : "Join the journey"}<ArrowUpRight size={17} /></Link></div><div className="cc-footer-bottom"><span>© {new Date().getFullYear()} Elqovanta EV</span><span>Made for more connected journeys.</span>{reducedMotion ? <span>Reduced motion enabled</span> : <button className="cc-motion-control" type="button" aria-pressed={paused} onClick={() => setPaused(!paused)}>{paused ? <Play size={13} /> : <Pause size={13} />}{paused ? "Resume animations" : "Pause animations"}</button>}</div></footer>
  </div>;
}
