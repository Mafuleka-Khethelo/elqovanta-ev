import { useEffect, type RefObject } from "react";

/** One observer and one animation frame for the entire landing page. */
export function useLandingMotion(root: RefObject<HTMLDivElement | null>, enabled: boolean) {
  useEffect(() => {
    const page = root.current;
    if (!page) return;
    const elements = page.querySelectorAll<HTMLElement>("[data-reveal]");
    if (!enabled || !("IntersectionObserver" in window)) {
      elements.forEach((element) => element.classList.add("is-visible"));
      page.style.setProperty("--car-x", "0px");
      page.style.setProperty("--car-y", "0px");
      page.style.setProperty("--car-rotate", "0deg");
      return;
    }

    page.classList.add("cc-enhanced");
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    elements.forEach((element) => observer.observe(element));

    const hero = page.querySelector<HTMLElement>(".cc-hero");
    let frame = 0;
    let pointerX = 0;
    let pointerY = 0;
    let pointing = false;
    const finePointer = window.matchMedia("(pointer: fine)");

    function draw() {
      frame = 0;
      if (!hero) return;
      const bounds = hero.getBoundingClientRect();
      if (bounds.bottom < 0 || bounds.top > window.innerHeight) return;
      const progress = Math.max(0, Math.min(1, -bounds.top / bounds.height));
      const x = pointing ? ((pointerX - bounds.left) / bounds.width - 0.5) * 2 : 0;
      const y = pointing ? ((pointerY - bounds.top) / bounds.height - 0.5) * 2 : 0;
      page!.style.setProperty("--car-x", `${(x * 12).toFixed(2)}px`);
      page!.style.setProperty("--car-y", `${(y * 7 + progress * 48).toFixed(2)}px`);
      page!.style.setProperty("--car-rotate", `${(x * -0.8).toFixed(2)}deg`);
    }
    function schedule() {
      if (!frame) frame = requestAnimationFrame(draw);
    }
    function move(event: PointerEvent) {
      if (!finePointer.matches) return;
      pointing = true;
      pointerX = event.clientX;
      pointerY = event.clientY;
      schedule();
    }
    function leave() {
      pointing = false;
      schedule();
    }

    hero?.addEventListener("pointermove", move, { passive: true });
    hero?.addEventListener("pointerleave", leave);
    window.addEventListener("scroll", schedule, { passive: true });
    schedule();
    return () => {
      observer.disconnect();
      hero?.removeEventListener("pointermove", move);
      hero?.removeEventListener("pointerleave", leave);
      window.removeEventListener("scroll", schedule);
      cancelAnimationFrame(frame);
    };
  }, [root, enabled]);
}
