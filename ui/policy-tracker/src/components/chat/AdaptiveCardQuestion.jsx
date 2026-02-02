import { useEffect, useRef, useCallback } from 'react'
import * as AdaptiveCards from 'adaptivecards'

/**
 * Renders Claude's clarifying questions as an Adaptive Card.
 *
 * When Claude needs more information to complete a task, it calls
 * the AskUserQuestion tool. This component renders those questions
 * as an interactive Adaptive Card with options and custom input.
 */
function AdaptiveCardQuestion({ questions, sessionId, onAnswerSubmit }) {
  const cardContainerRef = useRef(null)

  // Memoize the submit handler to prevent unnecessary re-renders
  const handleSubmit = useCallback((formattedAnswers) => {
    onAnswerSubmit(formattedAnswers)
  }, [onAnswerSubmit])

  useEffect(() => {
    if (!cardContainerRef.current || !questions?.length) return

    // Build Adaptive Card JSON from questions
    const cardPayload = {
      type: 'AdaptiveCard',
      $schema: 'http://adaptivecards.io/schemas/adaptive-card.json',
      version: '1.5',
      body: [],
      actions: [
        {
          type: 'Action.Submit',
          title: 'Submit',
          style: 'positive'
        }
      ]
    }

    // Add each question to the card
    questions.forEach((q, qIndex) => {
      // Header
      cardPayload.body.push({
        type: 'TextBlock',
        text: q.header,
        weight: 'Bolder',
        size: 'Medium',
        spacing: qIndex > 0 ? 'Large' : 'None'
      })

      // Question text
      cardPayload.body.push({
        type: 'TextBlock',
        text: q.question,
        wrap: true,
        spacing: 'Small'
      })

      // Options as choice set
      if (q.options && q.options.length > 0) {
        cardPayload.body.push({
          type: 'Input.ChoiceSet',
          id: `question_${qIndex}`,
          style: 'expanded',
          isMultiSelect: q.multiSelect || false,
          choices: q.options.map(opt => ({
            title: `${opt.label} - ${opt.description}`,
            value: opt.label
          }))
        })
      }

      // Custom input option
      cardPayload.body.push({
        type: 'Input.Text',
        id: `custom_${qIndex}`,
        placeholder: 'Or type your own answer...',
        spacing: 'Small'
      })
    })

    // Create and render the card
    const adaptiveCard = new AdaptiveCards.AdaptiveCard()

    // Configure card styling to match the app theme
    adaptiveCard.hostConfig = new AdaptiveCards.HostConfig({
      fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
      fontSizes: {
        small: 12,
        default: 14,
        medium: 16,
        large: 18,
        extraLarge: 22
      },
      fontWeights: {
        lighter: 300,
        default: 400,
        bolder: 600
      },
      containerStyles: {
        default: {
          backgroundColor: '#f8fafc',
          foregroundColors: {
            default: {
              default: '#1e293b',
              subtle: '#64748b'
            },
            accent: {
              default: '#3b82f6',
              subtle: '#60a5fa'
            }
          }
        }
      },
      actions: {
        actionAlignment: 'stretch',
        actionsOrientation: 'horizontal',
        buttonSpacing: 8,
        maxActions: 5,
        spacing: 'default',
        showCard: {
          actionMode: 'inline',
          inlineTopMargin: 16
        }
      },
      inputs: {
        choiceSet: {
          defaultCheckboxStyle: 'default',
          defaultRadioButtonStyle: 'default'
        }
      },
      spacing: {
        small: 4,
        default: 8,
        medium: 12,
        large: 16,
        extraLarge: 24,
        padding: 16
      }
    })

    // Handle submit action
    adaptiveCard.onExecuteAction = (action) => {
      if (action instanceof AdaptiveCards.SubmitAction) {
        const inputs = action.data || {}
        const formattedAnswers = {}

        questions.forEach((q, qIndex) => {
          const choiceValue = inputs[`question_${qIndex}`]
          const customValue = inputs[`custom_${qIndex}`]

          // Prefer custom input if provided, otherwise use choice
          const answer = customValue?.trim() || choiceValue || ''
          if (answer) {
            // For multi-select, the value is already comma-separated
            formattedAnswers[q.question] = answer
          }
        })

        handleSubmit(formattedAnswers)
      }
    }

    // Parse and render the card
    adaptiveCard.parse(cardPayload)
    const renderedCard = adaptiveCard.render()

    // Clear and append to container
    if (cardContainerRef.current) {
      cardContainerRef.current.innerHTML = ''
      if (renderedCard) {
        cardContainerRef.current.appendChild(renderedCard)
      }
    }

    // Cleanup on unmount
    return () => {
      if (cardContainerRef.current) {
        cardContainerRef.current.innerHTML = ''
      }
    }
  }, [questions, handleSubmit])

  if (!questions?.length) return null

  return (
    <div className="my-4 p-4 bg-blue-50 border border-blue-200 rounded-xl shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">🤔</span>
        <span className="text-blue-700 text-sm font-medium">
          Claude needs more information to continue
        </span>
      </div>
      <div
        ref={cardContainerRef}
        className="adaptive-card-container"
        style={{
          // Override some default Adaptive Card styles
          '--ac-accent-color': '#3b82f6',
        }}
      />
    </div>
  )
}

export default AdaptiveCardQuestion
