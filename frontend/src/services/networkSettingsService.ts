import { invokeNative } from '../api/native'
import type { NativeRecord } from '../types/native'

export const networkSettingsService = {
	get() {
		return invokeNative('GetNetworkPreferences')
	},

	save(settings: NativeRecord) {
		return invokeNative('UpdateNetworkPreferences', settings || {})
	},

	chooseCertificate() {
		return invokeNative('ChooseCertificateBundle')
	},

	choosePrivateKey() {
		return invokeNative('ChoosePrivateKey')
	},
}

export default networkSettingsService
