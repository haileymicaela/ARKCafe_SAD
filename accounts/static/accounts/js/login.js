
document.addEventListener("DOMContentLoaded", function () {
  const button = document.getElementById("toggle-password");

  if (!button) return;

  const input = document.getElementById(button.getAttribute("aria-controls"));
  const iconShow = button.querySelector(".icon-show");
  const iconHide = button.querySelector(".icon-hide");

  if (!input) return;

  button.addEventListener("click", function () {
    const reveal = input.type === "password";

    input.type = reveal ? "text" : "password";
    button.setAttribute("aria-pressed", String(reveal));
    button.setAttribute("aria-label", reveal ? "Hide password" : "Show password");

    if (iconShow) iconShow.hidden = reveal;
    if (iconHide) iconHide.hidden = !reveal;

    input.focus();
  });
});
