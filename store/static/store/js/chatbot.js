let step = 0;
let chatData = {};

const chatBox = document.getElementById("chatBox");
const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");

/* ---------- Utility Functions ---------- */

function addMessage(text, sender = "bot") {
  const div = document.createElement("div");
  div.className = `chat ${sender}`;
  div.innerHTML = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function resetChat() {
  step = 0;
  chatData = {};
  addMessage("🔄 Sure! Let’s find another pump.");
  addMessage("What is the required water depth (in ft)?");
}

/* ---------- Validation Functions ---------- */

function isValidDepth(value) {
  return !isNaN(value) && Number(value) > 0 && Number(value) <= 1000;
}

function isValidUsage(value) {
  return ["domestic", "agriculture", "industrial"].includes(value);
}

function isValidPhase(value) {
  return ["single", "three"].includes(value);
}

function isValidBudget(value) {
  return value === "" || (!isNaN(value) && Number(value) > 0);
}

/* ---------- Chatbot Logic ---------- */
chatForm.addEventListener("submit", function (e) {
  e.preventDefault();

  let rawInput = userInput.value;
  let input = rawInput.trim().toLowerCase();

  addMessage(input || "(skipped)", "user");
  userInput.value = "";

  /* STEP 0: DEPTH */
  if (step === 0) {
    if (!isValidDepth(input)) {
      addMessage("❌ Please enter a valid depth in feet (example: 120).");
      return;
    }
    chatData.depth_ft = input;
    addMessage("Great 👍 What is the usage type? (domestic / agriculture / industrial)");
    step = 1;
  }

  /* STEP 1: USAGE */
  else if (step === 1) {
    if (!isValidUsage(input)) {
      addMessage("❌ Invalid usage type. Enter: domestic, agriculture, or industrial.");
      return;
    }
    chatData.usage_type = input;
    addMessage("Which phase do you have? (single / three)");
    step = 2;
  }

  /* STEP 2: PHASE */
  else if (step === 2) {
    if (!isValidPhase(input)) {
      addMessage("❌ Invalid phase. Enter: single or three.");
      return;
    }
    chatData.phase = input;
    addMessage("What is your maximum budget? (optional — press Enter to skip)");
    step = 3;
  }

  /* STEP 3: BUDGET (ALLOW EMPTY INPUT) */
  else if (step === 3) {
    if (input !== "" && !isValidBudget(input)) {
      addMessage("❌ Please enter a valid budget or press Enter to skip.");
      return;
    }

    if (input !== "") {
      chatData.budget = input;
    }

    addMessage("🔍 Finding the best pumps for you...");

    fetch("/api/recommend-pump/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(chatData)
    })
      .then(res => res.json())
      .then(data => {
        if (!data.recommendations || data.recommendations.length === 0) {
          addMessage("❌ Sorry, no suitable pumps found.");
        } else {
            data.recommendations.forEach(pump => {
            addMessage(`
              <strong>${pump.name}</strong><br>
              Model: ${pump.model_number}<br>
              Power: ${pump.motor_power_hp} HP<br>
              Max Depth: ${pump.max_depth_ft} ft<br>
              Price: ₹${pump.price}<br>
              <a href="${pump.product_url}" class="btn btn-sm btn-outline-primary mt-2">
                View Product
              </a>
            `);
          });
        }

        addMessage("👉 Would you like another pump recommendation? (yes / no)");
        step = 4;   // 🔥 IMPORTANT
      });
  }

  /* STEP 4: RESTART OR END */
  else if (step === 4) {
    if (input === "yes") {
      step = 0;
      chatData = {};
      addMessage("🔄 Sure! Let’s start again.");
      addMessage("What is the required water depth (in ft)?");
    }
    else if (input === "no") {
      addMessage("😊 Thank you for using Smart Pump Assistant. Have a great day!");
      step = 5;
    }
    else {
      addMessage("❓ Please reply with 'yes' or 'no'.");
    }
  }
});
