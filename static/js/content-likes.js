
document.addEventListener("DOMContentLoaded", function () {
    const likeForms = document.querySelectorAll("[data-like-form]");

    likeForms.forEach(form => {
        form.addEventListener("submit", async function (event) {
            event.preventDefault();

            const button = form.querySelector(".content-like-btn");
            const icon = button.querySelector(".like-icon");
            const count = button.querySelector(".like-count");

            const csrfToken = form.querySelector(
                '[name="csrfmiddlewaretoken"]'
            )?.value;

            if (!csrfToken || button.disabled) return;

            button.disabled = true;

            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "X-Requested-With": "XMLHttpRequest",
                        "Accept": "application/json"
                    },
                    credentials: "same-origin"
                });

                const data = await response.json();

                if (!response.ok || !data.success) {
                    throw new Error(
                        data.message || "Gagal memperbarui Like."
                    );
                }

                // Jika tombol berada di halaman koleksi
                if (
                    form.dataset.removeCard === "true" &&
                    !data.liked
                ) {
                    const card = form.closest(".liked-content-card");

                    if (card) {
                        card.remove();
                    }

                    const remainingCards = document.querySelectorAll(
                        ".liked-content-card"
                    );

                    const resultCount = document.querySelector(
                        ".likes-result-count"
                    );

                    if (resultCount) {
                        resultCount.textContent =
                            `${remainingCards.length} konten ditampilkan`;
                    }

                    const totalCount = document.querySelector(
                        ".likes-hero-stat strong"
                    );

                    if (totalCount) {
                        const current = Number(totalCount.textContent);
                        totalCount.textContent = Math.max(0, current - 1);
                    }

                    // Tampilkan empty state jika tidak ada kartu lagi
                    if (remainingCards.length === 0) {
                        window.location.reload();
                    }

                    return;
                }

                // Perbarui tombol Like di halaman detail
                button.classList.toggle("is-liked", data.liked);

                icon.textContent = data.liked ? "♥" : "♡";

                if (count) {
                    count.textContent = data.total_likes;
                }

                button.setAttribute(
                    "aria-pressed",
                    String(data.liked)
                );

                button.setAttribute(
                    "aria-label",
                    data.liked ? "Batalkan like" : "Sukai konten"
                );

            } catch (error) {
                console.error("Like error:", error);
                alert(error.message || "Terjadi kesalahan.");
            } finally {
                button.disabled = false;
            }
        });
    });
});
