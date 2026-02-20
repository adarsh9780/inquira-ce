class FactService {
  constructor() {
    this.facts = []
    this.currentIndex = 0
    this.intervalId = null
    this.isLoaded = false
    this.onFactChange = null
  }

  // Load facts from JSON file
  async loadFacts() {
    if (this.isLoaded) return

    try {
      const response = await fetch('/human-body-facts.json')
      if (!response.ok) {
        throw new Error('Failed to load facts')
      }
      this.facts = await response.json()
      this.isLoaded = true
      console.debug(`✅ Loaded ${this.facts.length} human body facts`)
    } catch (error) {
      console.error('❌ Failed to load facts:', error)
      // Fallback facts in case JSON loading fails
      this.facts = [
        "The human body contains about 100 trillion cells.",
        "Your heart beats around 100,000 times per day.",
        "The human brain uses about 20% of the body's total energy.",
        "There are 206 bones in the adult human body.",
        "The human eye can distinguish about 10 million colors."
      ]
      this.isLoaded = true
    }
  }

  // Get current fact
  getCurrentFact() {
    if (!this.isLoaded || this.facts.length === 0) {
      return "Loading interesting facts..."
    }
    return this.facts[this.currentIndex]
  }

  // Get next fact
  getNextFact() {
    if (!this.isLoaded || this.facts.length === 0) {
      return "Loading interesting facts..."
    }
    this.currentIndex = (this.currentIndex + 1) % this.facts.length
    return this.facts[this.currentIndex]
  }

  // Start fact rotation every 5 seconds
  startRotation(callback) {
    this.onFactChange = callback

    // Set up interval for rotation (no initial fact to avoid duplication)
    this.intervalId = setInterval(() => {
      const nextFact = this.getNextFact()
      if (this.onFactChange) {
        this.onFactChange(nextFact)
      }
    }, 5000) // 5 seconds

    console.debug('🎯 Started fact rotation every 5 seconds')
  }

  // Stop fact rotation
  stopRotation() {
    if (this.intervalId) {
      clearInterval(this.intervalId)
      this.intervalId = null
      console.debug('🛑 Stopped fact rotation')
    }
  }

  // Set callback for fact changes
  setFactChangeCallback(callback) {
    this.onFactChange = callback
  }

  // Get total number of facts
  getTotalFacts() {
    return this.facts.length
  }

  // Get current fact index
  getCurrentIndex() {
    return this.currentIndex
  }
}

// Create singleton instance
export const factService = new FactService()
export default factService