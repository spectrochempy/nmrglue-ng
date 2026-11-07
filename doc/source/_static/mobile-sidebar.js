document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector("#pst-header button.primary-toggle");
  const drawer = document.getElementById("pst-primary-sidebar-modal");
  if (!toggle || !drawer) return;

  toggle.setAttribute("aria-haspopup", "dialog");
  toggle.setAttribute("aria-controls", drawer.id);
  drawer.setAttribute("aria-label", toggle.getAttribute("aria-label") || "Site navigation");

  const close = document.createElement("button");
  close.type = "button";
  close.className = "btn ng-sidebar-close";
  close.textContent = "Close navigation";
  close.addEventListener("click", () => drawer.close());
  toggle.addEventListener("click", () => {
    queueMicrotask(() => {
      if (drawer.open) drawer.prepend(close);
    });
  });

  // The book theme blurs the toggle on activation, so the dialog has no focus
  // target to restore by itself.
  drawer.addEventListener("close", () => {
    close.remove();
    if (toggle.getClientRects().length) toggle.focus({ preventScroll: true });
  });
});
