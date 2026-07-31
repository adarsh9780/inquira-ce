import { describe, expect, it } from 'vitest'

import {
  mapTurnToChatMessage,
  selectDisplayedChatHistory,
} from '../src/utils/chatHistoryView'

describe('chat history view selection', () => {
  it('keeps the completed local answer after its temporary message ID is linked to a turn', () => {
    const completedMessage = {
      id: 'pending-123',
      turnId: 'turn-456',
      question: 'Show the top batsmen',
      explanation: 'Virat Kohli leads the table.',
      analysisMetadata: { tables_used: ['ball_by_ball_ipl'] },
    }

    const displayed = selectDisplayedChatHistory({
      localHistory: [completedMessage],
      activeTurnId: 'turn-456',
      activeTurn: {
        id: 'turn-456',
        user_text: 'Show the top batsmen',
        assistant_text: '',
        metadata: { tables_used: ['ball_by_ball_ipl'] },
      },
      isRunning: false,
    })

    expect(displayed).toEqual([completedMessage])
    expect(displayed[0]?.explanation).toBe('Virat Kohli leads the table.')
  })

  it('recovers a persisted answer from final-response metadata when needed', () => {
    const message = mapTurnToChatMessage({
      id: 'turn-456',
      user_text: 'Show the top batsmen',
      assistant_text: '',
      metadata: {
        final_response: { answer: 'Virat Kohli leads the table.' },
      },
    })

    expect(message?.explanation).toBe('Virat Kohli leads the table.')
  })
})
