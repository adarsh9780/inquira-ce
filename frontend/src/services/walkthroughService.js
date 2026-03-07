import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'
import { uiPreferencesService } from './uiPreferencesService'

const WALKTHROUGH_STEPS = [
    {
        element: '.min-h-screen', // Fallback to full screen if nothing specific
        popover: {
            title: 'Welcome to Inquira!',
            description: 'Let\'s take a quick tour of the interface to help you get started.',
            side: 'bottom',
            align: 'start'
        }
    },
    {
        element: '.w-64.border-r', // The UnifiedSidebar
        popover: {
            title: 'Sidebar',
            description: 'Here you can navigate between Workspaces, Datasets, and Conversations.',
            side: 'right',
            align: 'start'
        }
    },
    {
        element: '.flex-1.flex.flex-col.overflow-hidden > .flex', // The RightPanel's horizontal split
        popover: {
            title: 'Workspace Area',
            description: 'This is where the magic happens. It is split into a left pane for Chat/Code and a right pane for Results/Data.',
            side: 'top',
            align: 'center'
        }
    },
    {
        element: '.border-t.p-2.shrink-0', // Bottom of Sidebar
        popover: {
            title: 'Quick Actions',
            description: 'Access the global Schema Editor or return to your Workspaces from here.',
            side: 'right',
            align: 'end'
        }
    }
]

export const walkthroughService = {
    async startIfFirstTime() {
        try {
            const hasSeen = await uiPreferencesService.hasSeenWalkthrough()
            if (hasSeen) return

            // Delay slightly to ensure UI is fully rendered and animations (like sidebar sliding in) complete
            setTimeout(() => {
                const driverObj = driver({
                    showProgress: true,
                    steps: WALKTHROUGH_STEPS,
                    onDestroyStarted: () => {
                        if (!driverObj.hasNextStep() || confirm("Are you sure you want to skip the remaining tour?")) {
                            uiPreferencesService.markWalkthroughAsSeen().then(() => {
                                driverObj.destroy()
                            }).catch(() => {
                                driverObj.destroy()
                            })
                        }
                    },
                })

                driverObj.drive()
            }, 500)
        } catch (error) {
            console.error('Walkthrough error:', error)
        }
    }
}
