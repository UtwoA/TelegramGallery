(function () {
  function initUploadForm() {
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");
    const form = document.getElementById("upload-form");
    const statusNode = document.getElementById("upload-status");
    const progressWrap = document.getElementById("progress-bar");
    const progressBar = progressWrap ? progressWrap.querySelector("span") : null;

    if (!dropzone || !fileInput || !form) return;

    const setFiles = (files) => {
      fileInput.files = files;
      if (statusNode) statusNode.textContent = `Выбрано файлов: ${files.length}`;
    };

    dropzone.addEventListener("click", () => fileInput.click());

    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.add("drag-over");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropzone.classList.remove("drag-over");
      });
    });

    dropzone.addEventListener("drop", (e) => {
      if (!e.dataTransfer || !e.dataTransfer.files) return;
      setFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files) setFiles(fileInput.files);
    });

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      if (!fileInput.files || fileInput.files.length === 0) {
        if (statusNode) statusNode.textContent = "Добавьте хотя бы один файл";
        return;
      }

      const formData = new FormData(form);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", form.action);
      xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");

      if (progressWrap && progressBar) {
        progressWrap.classList.remove("hidden");
        progressBar.style.width = "0%";
      }

      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable || !progressBar) return;
        const pct = Math.round((event.loaded / event.total) * 100);
        progressBar.style.width = `${pct}%`;
        if (statusNode) statusNode.textContent = `Загрузка: ${pct}%`;
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          if (statusNode) statusNode.textContent = "Файлы успешно загружены";
          setTimeout(() => {
            window.location.href = "/all-photos";
          }, 450);
        } else {
          if (statusNode) statusNode.textContent = "Ошибка загрузки";
        }
      };

      xhr.onerror = () => {
        if (statusNode) statusNode.textContent = "Сетевая ошибка при загрузке";
      };

      xhr.send(formData);
    });
  }

  function initSectionToggle() {
    const toggleButtons = document.querySelectorAll(".section-toggle");
    if (!toggleButtons.length) return;

    toggleButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const groupId = btn.dataset.target;
        if (!groupId) return;

        const grid = document.querySelector(`.showcase-grid[data-group='${groupId}']`);
        if (!grid) return;

        const extraCards = grid.querySelectorAll(".extra-card");
        const expanded = btn.getAttribute("aria-expanded") === "true";

        extraCards.forEach((card) => {
          card.classList.toggle("is-hidden", expanded);
        });

        if (expanded) {
          btn.setAttribute("aria-expanded", "false");
          btn.textContent = `Раскрыть раздел (+${btn.dataset.hiddenCount || extraCards.length})`;
        } else {
          btn.setAttribute("aria-expanded", "true");
          btn.textContent = "Свернуть раздел";
        }
      });
    });
  }

  function initScrollReveal() {
    const items = document.querySelectorAll(".reveal");
    if (!items.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -30px 0px" }
    );

    items.forEach((node) => observer.observe(node));
  }

  function initBulkSelection() {
    const bulkForm = document.getElementById("bulk-form");
    if (!bulkForm) return;

    const checkboxes = Array.from(document.querySelectorAll(".bulk-checkbox"));
    const selectedCountNode = document.getElementById("selected-count");
    const submitBtn = document.getElementById("bulk-submit-btn");
    const selectAllBtn = document.getElementById("select-all-btn");
    const clearSelectionBtn = document.getElementById("clear-selection-btn");
    const sectionButtons = document.querySelectorAll(".select-section-btn");

    const refreshSelectionState = () => {
      const selectedCount = checkboxes.filter((cb) => cb.checked).length;
      if (selectedCountNode) selectedCountNode.textContent = String(selectedCount);
      if (submitBtn) submitBtn.disabled = selectedCount === 0;
    };

    checkboxes.forEach((cb) => {
      cb.addEventListener("change", refreshSelectionState);
    });

    if (selectAllBtn) {
      selectAllBtn.addEventListener("click", () => {
        checkboxes.forEach((cb) => {
          cb.checked = true;
        });
        refreshSelectionState();
      });
    }

    if (clearSelectionBtn) {
      clearSelectionBtn.addEventListener("click", () => {
        checkboxes.forEach((cb) => {
          cb.checked = false;
        });
        refreshSelectionState();
      });
    }

    sectionButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const sectionId = btn.dataset.section;
        if (!sectionId) return;
        checkboxes.forEach((cb) => {
          if (cb.dataset.sectionItem === sectionId) {
            cb.checked = true;
          }
        });
        refreshSelectionState();
      });
    });

    bulkForm.addEventListener("submit", (event) => {
      const selectedCount = checkboxes.filter((cb) => cb.checked).length;
      if (selectedCount === 0) {
        event.preventDefault();
        return;
      }

      const deleteAction = bulkForm.querySelector("select[name='delete_action']");
      if (deleteAction && deleteAction.value === "delete") {
        const ok = window.confirm(`Удалить выбранные файлы (${selectedCount}) безвозвратно?`);
        if (!ok) {
          event.preventDefault();
          return;
        }
      }
    });

    refreshSelectionState();
  }

  function initShowreelCarousel() {
    const root = document.getElementById("showreel-carousel");
    if (!root) return;

    const track = root.querySelector("[data-carousel-track]");
    const dotsWrap = root.querySelector("[data-carousel-dots]");
    const prevBtn = root.querySelector("[data-carousel-prev]");
    const nextBtn = root.querySelector("[data-carousel-next]");
    if (!track || !dotsWrap) return;

    const slides = Array.from(track.children);
    const dots = Array.from(dotsWrap.children);
    if (!slides.length || !dots.length) return;

    let current = 0;
    let timer = null;

    const goTo = (idx) => {
      current = (idx + slides.length) % slides.length;
      track.style.transform = `translateX(-${current * 100}%)`;
      dots.forEach((dot, i) => {
        dot.classList.toggle("is-active", i === current);
      });
    };

    const startAutoplay = () => {
      stopAutoplay();
      timer = window.setInterval(() => {
        goTo(current + 1);
      }, 4200);
    };

    const stopAutoplay = () => {
      if (timer) {
        window.clearInterval(timer);
        timer = null;
      }
    };

    dots.forEach((dot, idx) => {
      dot.addEventListener("click", () => {
        goTo(idx);
        startAutoplay();
      });
    });

    if (prevBtn) {
      prevBtn.addEventListener("click", () => {
        goTo(current - 1);
        startAutoplay();
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", () => {
        goTo(current + 1);
        startAutoplay();
      });
    }

    root.addEventListener("mouseenter", stopAutoplay);
    root.addEventListener("mouseleave", startAutoplay);
    root.addEventListener("touchstart", stopAutoplay, { passive: true });
    root.addEventListener("touchend", startAutoplay, { passive: true });

    goTo(0);
    startAutoplay();
  }

  function initShowreelLightbox() {
    const root = document.getElementById("showreel-carousel");
    const modal = document.getElementById("showreel-lightbox");
    const modalContent = document.getElementById("showreel-lightbox-content");
    const closeBtn = document.getElementById("showreel-lightbox-close");
    if (!root || !modal || !modalContent || !closeBtn) return;

    const items = root.querySelectorAll("[data-lightbox-item]");
    if (!items.length) return;

    const close = () => {
      modal.classList.add("hidden");
      modal.setAttribute("aria-hidden", "true");
      modalContent.innerHTML = "";
      document.body.classList.remove("lightbox-open");
    };

    items.forEach((item) => {
      item.addEventListener("click", (event) => {
        if (event.target && event.target.closest("video")) {
          return;
        }

        const img = item.querySelector("img");
        const video = item.querySelector("video");
        modalContent.innerHTML = "";

        if (video) {
          const cloneVideo = document.createElement("video");
          cloneVideo.controls = true;
          cloneVideo.autoplay = true;
          cloneVideo.loop = true;
          cloneVideo.playsInline = true;
          cloneVideo.muted = true;
          if (video.poster) cloneVideo.poster = video.poster;

          const source = video.querySelector("source");
          if (source && source.src) {
            const s = document.createElement("source");
            s.src = source.src;
            s.type = source.type || "video/mp4";
            cloneVideo.appendChild(s);
          }
          modalContent.appendChild(cloneVideo);
        } else if (img) {
          const cloneImg = document.createElement("img");
          cloneImg.src = img.currentSrc || img.src;
          cloneImg.alt = img.alt || "Showreel item";
          modalContent.appendChild(cloneImg);
        }

        modal.classList.remove("hidden");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("lightbox-open");
      });
    });

    closeBtn.addEventListener("click", close);
    modal.addEventListener("click", (event) => {
      if (event.target === modal) close();
    });
    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !modal.classList.contains("hidden")) {
        close();
      }
    });
  }

  initUploadForm();
  initSectionToggle();
  initScrollReveal();
  initBulkSelection();
  initShowreelCarousel();
  initShowreelLightbox();
})();
