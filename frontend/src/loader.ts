// What Home Assistant loads on every page. While it boots, Home Assistant installs its custom
// element registry (in Firefox, a stand-in for scoped registries). Cards defined before that land
// in a registry it never reads, so, as Loona does, wait until it is ready, then load the cards.

const cards = new URL(`gac-connect-cards-main.js${new URL(import.meta.url).search}`, import.meta.url).href;

function start(): void {
  const app = document.querySelector("home-assistant") as (Element & { hass?: unknown }) | null;
  if (!app?.hass) {
    window.setTimeout(start, 100);
    return;
  }
  import(/* @vite-ignore */ cards).catch((error) => console.error("GAC Connect cards could not load", error));
}

start();
