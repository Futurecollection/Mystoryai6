// Complete character data structures for each pre-made bio
const characterBios = {
  // Tech CEO - Emma
  "emma": {
    bio: `Emma Chen is a 32-year-old tech CEO who has transformed her startup into one of Silicon Valley's most innovative companies. With sleek black hair typically worn in a sophisticated low bun, striking amber eyes, and a confident smile, she commands attention in any room. Standing at 5'7" with an athletic build maintained through dawn yoga and evening runs, she carries herself with unmistakable poise. Emma typically dresses in tailored blazers, silk blouses, and slim pants, with a signature gold pendant necklace that was her grandmother's. She's known for her sharp intellect, strategic thinking, and surprising warmth once you break through her professional exterior. Between board meetings and product launches, she's looking for someone who can keep up with her fast-paced lifestyle but also remind her to slow down and enjoy life's simpler pleasures.`,

    // Character attributes
    name: "Emma Chen",
    gender: "Female",
    age: "32",
    ethnicity: "Chinese American",
    sexual_orientation: "Straight",
    relationship_goal: "Casual Dating",
    body_type: "Athletic",
    hair_color: "Black",
    hair_style: "Sophisticated low bun",
    personality: "Confident and Ambitious",
    clothing: "Tailored blazers and silk blouses",
    occupation: "Tech CEO",
    current_situation: "Career-focused",

    // Environment details
    environment: "Upscale Wine Bar",
    encounter_context: "Mutual Friend's Introduction"
  },

  // Hollywood Actress - Scarlett
  "scarlett": {
    bio: `Scarlett Winters is a 28-year-old rising Hollywood actress who's just landed her breakthrough role in an acclaimed director's newest film. With flowing auburn hair that catches the light, captivating green eyes, and a smile that's graced countless magazine covers, she has a natural beauty that transcends the screen. At 5'6" with a graceful figure, she moves with an elegance cultivated through years of dance training. Today she's dressed down in designer jeans and a casual silk top, trying to remain incognito despite her growing fame. Beneath the glamorous exterior, Scarlett is surprisingly down-to-earth, with a quick wit and infectious laugh. While her career is soaring, she's increasingly aware of the hollowness of Hollywood connections and craves something authentic—someone who sees the woman behind the roles she plays.`,

    name: "Scarlett Winters",
    gender: "Female",
    age: "28",
    ethnicity: "Caucasian",
    sexual_orientation: "Bisexual",
    relationship_goal: "Looking for Connection",
    body_type: "Slender and Graceful",
    hair_color: "Auburn",
    hair_style: "Long and Flowing",
    personality: "Witty and Outgoing",
    clothing: "Designer jeans and casual silk top",
    occupation: "Actress",
    current_situation: "Career taking off",

    environment: "Quiet Corner Restaurant",
    encounter_context: "Chance Meeting"
  },

  // Fashion Designer - Zendaya
  "zendaya": {
    bio: `Zendaya Coleman is a 26-year-old fashion designer whose bold, avant-garde creations have made her the industry's newest darling. With her signature cloud of natural curls, warm brown eyes that miss no detail, and flawless skin, she embodies the artistic vision that defines her work. Standing tall at 5'10", her willowy frame showcases her own designs—today, a structured jumpsuit in a rich emerald tone that complements her complexion perfectly. Zendaya speaks with passionate intensity about her creative process but listens just as intently, finding inspiration in unexpected conversations. While her career demands extensive travel between Paris, Milan, and New York, she's hoping to find someone who appreciates both her ambitious drive and her need for quiet moments of creativity—a partner who understands that her occasional distraction isn't distance but the spark of new ideas taking form.`,

    name: "Zendaya Coleman",
    gender: "Female",
    age: "26",
    ethnicity: "Black/African American",
    sexual_orientation: "Straight",
    relationship_goal: "Serious Relationship",
    body_type: "Tall and Willowy",
    hair_color: "Dark Brown",
    hair_style: "Natural Curls",
    personality: "Creative and Passionate",
    clothing: "Structured jumpsuit in emerald",
    occupation: "Fashion Designer",
    current_situation: "Frequent traveler for work",

    environment: "Art Gallery Opening",
    encounter_context: "Professional Event"
  },

  // International Journalist - Natalia
  "natalie": {
    bio: `Natalia Petrova is a 30-year-old international journalist known for her fearless frontline reporting and insightful political analysis. Her shoulder-length dark blonde hair is usually pulled back in a practical style, framing intense blue eyes that have witnessed events that changed history. With a toned physique from years of navigating challenging terrain, she carries herself with easy confidence. Having just returned from an assignment abroad, she's dressed in a simple blue button-down and well-worn jeans, her only adornment a vintage camera pendant—a gift from her mentor. Natalia speaks five languages fluently and has an uncanny ability to make anyone feel heard and understood. Though her schedule is unpredictable and she's often called away on assignments with little notice, she's reached a point where she's seeking something—or someone—worth coming home to.`,

    name: "Natalia Petrova",
    gender: "Female",
    age: "30",
    ethnicity: "Russian",
    sexual_orientation: "Straight",
    relationship_goal: "Open Relationship",
    body_type: "Toned",
    hair_color: "Dark Blonde",
    hair_style: "Practical shoulder-length",
    personality: "Intense and Intelligent",
    clothing: "Simple blue button-down and jeans",
    occupation: "International Journalist",
    current_situation: "Just returned from assignment",

    environment: "Quiet Cafe",
    encounter_context: "Random Encounter"
  },

  // Fitness Entrepreneur - Henry
  "henry": {
    bio: `Henry Cavill is a 34-year-old former professional athlete who now runs a successful chain of boutique fitness studios. With his muscular 6'2" frame, close-cropped dark hair, and striking blue eyes, he still looks the part of the championship athlete he once was. A small scar above his right eyebrow tells of past competitive intensity. Today he's wearing fitted athletic wear from his own brand—simple, high-quality pieces that emphasize functionality. Henry's serious demeanor breaks easily into a warm, genuine smile, especially when discussing topics he's passionate about: physical well-being, entrepreneurship, and his nonprofit providing sports opportunities to underprivileged youth. Despite his professional success, years focused solely on his career have left little room for meaningful connection, something he's increasingly aware of as his business stabilizes and he looks to what's next in his life journey.`,

    name: "Henry Cavill",
    gender: "Male",
    age: "34",
    ethnicity: "British",
    sexual_orientation: "Straight",
    relationship_goal: "Long-term Relationship",
    body_type: "Muscular",
    hair_color: "Dark Brown",
    hair_style: "Close-cropped",
    personality: "Determined and Passionate",
    clothing: "Fitted athletic wear",
    occupation: "Fitness Entrepreneur",
    current_situation: "Business owner seeking balance",

    environment: "Charity Gala",
    encounter_context: "Friend's Introduction"
  },

  // Marine Biologist - Chris
  "chris": {
    bio: `Chris Hemsworth is a 31-year-old marine biologist whose groundbreaking research on coral reef preservation has recently earned him international recognition. His sun-streaked blonde hair and tanned skin reveal countless hours spent on research vessels and underwater expeditions. Standing at 6'3" with broad shoulders and an easy, confident stance, he has the powerful build of someone who spends their days swimming and diving. His most striking feature is his expressive blue-green eyes that light up when discussing his work. Chris is dressed casually in a well-worn henley and khaki shorts, with a handmade bracelet of salvaged fishing line from his last expedition. Despite his scientific precision at work, he approaches life with laid-back humor and genuine curiosity about others' experiences. After years of prioritizing remote research locations, he's taking a sabbatical to write a book and, perhaps, find someone who shares his passion for protecting the natural world.`,

    name: "Chris Hemsworth",
    gender: "Male",
    age: "31",
    ethnicity: "Australian",
    sexual_orientation: "Straight",
    relationship_goal: "Taking Things Slow",
    body_type: "Athletic and Tanned",
    hair_color: "Sun-streaked Blonde",
    hair_style: "Casual medium length",
    personality: "Laid-back and Passionate",
    clothing: "Henley and khaki shorts",
    occupation: "Marine Biologist",
    current_situation: "Taking a sabbatical",

    environment: "Beachfront Cafe",
    encounter_context: "Chance Meeting"
  }
};

// Function to update bio text and character attributes in the form
function updateBioText() {
    const selectedBio = document.getElementById('predefinedBios').value;
    const bioTextArea = document.getElementById('bioTextArea');
    const bioText = document.getElementById('bioText');

    if (selectedBio && characterBios[selectedBio]) {
        bioTextArea.value = characterBios[selectedBio].bio;
        bioText.value = characterBios[selectedBio].bio;

        // Populate other form fields here (example)
        document.getElementById('name').value = characterBios[selectedBio].name;
        document.getElementById('age').value = characterBios[selectedBio].age;
        // Add more form field updates as needed...

    } else {
        bioTextArea.value = '';
        bioText.value = '';
        // Clear other form fields as needed...

    }
}

// Initialize when the document loads
document.addEventListener('DOMContentLoaded', function() {
    // Set up event listener for the bio selection
    const bioSelect = document.getElementById('predefinedBios');
    if (bioSelect) {
        bioSelect.addEventListener('change', updateBioText);
    }

    // Set up event listener for the textarea to update the hidden input
    const bioTextArea = document.getElementById('bioTextArea');
    const bioText = document.getElementById('bioText');
    if (bioTextArea && bioText) {
        bioTextArea.addEventListener('input', function() {
            bioText.value = bioTextArea.value;
        });
    }
});